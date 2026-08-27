import os
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
import streamlit as st

from dotenv import load_dotenv
from supabase import create_client

from src.generation.rag_chain import stream_answer
from src.retrieval.retriever import get_retriever
from src.logging_config.logger import get_logger

logger = get_logger(__name__)
logger.info("AI Assist application started")


# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="AI Assist - Insurance Policy Information System",
    page_icon="🛡️",
    layout="wide"
)


# ==================================================
# PATHS
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOGIN_IMAGE_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "ai_assist_login.png"
)




# ==================================================
# SESSION STATE
# ==================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "username" not in st.session_state:
    st.session_state.username = None


if "user_profile" not in st.session_state:
    st.session_state.user_profile = None


# ==================================================
# AUTHENTICATION DATABASE
# Supabase Auth + PostgreSQL profile / approval layer
# ==================================================

load_dotenv()


def get_config_value(name):
    """
    Local development:
        .env

    Streamlit Community Cloud:
        st.secrets
    """

    value = os.getenv(name)

    if value:
        return value

    try:
        return st.secrets[name]
    except Exception:
        return None


SUPABASE_URL = get_config_value("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = get_config_value(
    "SUPABASE_PUBLISHABLE_KEY"
)
SUPABASE_SECRET_KEY = get_config_value(
    "SUPABASE_SECRET_KEY"
)

ADMIN_USERNAME = get_config_value("ADMIN_USERNAME")
ADMIN_PASSWORD = get_config_value("ADMIN_PASSWORD")


def get_public_supabase_client():
    """
    Used for normal Supabase Auth operations:
    signup, login, password recovery.

    A new client is created per operation so authentication
    sessions are not shared between Streamlit users.
    """

    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:

        logger.error(
            "Supabase public authentication configuration is missing"
        )

        raise RuntimeError(
            "Supabase authentication configuration is missing."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY
    )


def get_service_supabase_client():
    """
    Server-side client used only inside the Streamlit backend
    for profile management and administrator operations.
    """

    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:

        logger.error(
            "Supabase service configuration is missing"
        )

        raise RuntimeError(
            "Supabase service configuration is missing."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY
    )


# --------------------------------------------------
# LEGACY PASSWORD SUPPORT
# --------------------------------------------------
# Existing users created before Supabase Auth are still
# supported so the authentication upgrade does not break
# already-created accounts.

PASSWORD_ITERATIONS = 600_000


def hash_password(password):

    salt = secrets.token_bytes(16)

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS
    )

    return (
        f"pbkdf2_sha256$"
        f"{PASSWORD_ITERATIONS}$"
        f"{salt.hex()}$"
        f"{derived_key.hex()}"
    )


def verify_password(
    password,
    stored_hash
):

    try:

        algorithm, iterations, salt_hex, hash_hex = (
            stored_hash.split("$", 3)
        )

        if algorithm != "pbkdf2_sha256":
            return False

        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations)
        ).hex()

        return hmac.compare_digest(
            candidate_hash,
            hash_hex
        )

    except (ValueError, AttributeError):
        return False


# --------------------------------------------------
# GOVERNMENT EMPLOYEE REGISTRATION
# --------------------------------------------------

def create_government_user(
    employee_name,
    email,
    password,
    employee_id,
    department
):

    employee_id = employee_id.strip()
    employee_name = employee_name.strip()
    email = email.strip().lower()
    department = department.strip()

    service_client = None
    auth_user_id = None

    try:

        service_client = get_service_supabase_client()

        existing = (
            service_client
            .table("government_users")
            .select("id")
            .or_(
                f"employee_id.eq.{employee_id},"
                f"email.eq.{email}"
            )
            .limit(1)
            .execute()
        )

        if existing.data:

            logger.warning(
                "Government registration rejected: "
                "Employee ID or email already exists"
            )

            return (
                False,
                "An account already exists with this "
                "Employee ID or email."
            )

        auth_client = get_public_supabase_client()

        auth_response = auth_client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "employee_id": employee_id,
                        "employee_name": employee_name,
                        "department": department
                    }
                }
            }
        )

        if not auth_response.user:

            return (
                False,
                "Unable to create the authentication account."
            )

        auth_user_id = str(
            auth_response.user.id
        )

        (
            service_client
            .table("government_users")
            .insert(
                {
                    "auth_user_id": auth_user_id,
                    "employee_id": employee_id,
                    "employee_name": employee_name,
                    "email": email,
                    "department": department,

                    # Existing table compatibility.
                    # New passwords are managed only by Supabase Auth.
                    "password_hash": "SUPABASE_AUTH",

                    "status": "pending",
                    "role": "government",
                    "is_active": True
                }
            )
            .execute()
        )

        logger.info(
            "Government employee registration created "
            "and placed in pending approval"
        )

        return (
            True,
            "Account created successfully. "
            "Please verify your email if Supabase sends a "
            "verification message, then wait for administrator approval."
        )

    except Exception as error:

        # If Auth succeeded but the profile insert failed,
        # remove the partial Auth user to keep the systems consistent.
        if auth_user_id and service_client:

            try:
                service_client.auth.admin.delete_user(
                    auth_user_id
                )
            except Exception:
                logger.exception(
                    "Unable to roll back incomplete Auth registration"
                )

        error_text = str(error).lower()

        if (
            "already registered" in error_text
            or "duplicate" in error_text
            or "unique" in error_text
            or "23505" in error_text
        ):

            logger.warning(
                "Government registration rejected: Duplicate account"
            )

            return (
                False,
                "An account already exists with this "
                "Employee ID or email."
            )

        logger.exception(
            "Government employee registration failed"
        )

        return (
            False,
            "Unable to create account. Please try again."
        )


# --------------------------------------------------
# GOVERNMENT LOGIN
# --------------------------------------------------

def validate_government_user(
    employee_id,
    password
):

    employee_id = employee_id.strip()

    try:

        service_client = get_service_supabase_client()

        response = (
            service_client
            .table("government_users")
            .select(
                "id, auth_user_id, employee_id, employee_name, "
                "email, department, password_hash, status, "
                "role, is_active"
            )
            .eq(
                "employee_id",
                employee_id
            )
            .limit(1)
            .execute()
        )

        if not response.data:

            logger.warning(
                "Government login failed: Employee ID not found"
            )

            return (
                None,
                "Invalid Employee ID or password."
            )

        user = response.data[0]

        auth_user_id = user.get(
            "auth_user_id"
        )

        email = user.get(
            "email"
        )

        # ------------------------------------------
        # NEW SUPABASE AUTH ACCOUNT
        # ------------------------------------------

        if auth_user_id and email:

            try:

                auth_client = get_public_supabase_client()

                auth_response = (
                    auth_client
                    .auth
                    .sign_in_with_password(
                        {
                            "email": email,
                            "password": password
                        }
                    )
                )

                if not auth_response.user:

                    return (
                        None,
                        "Invalid Employee ID or password."
                    )

            except Exception:

                logger.warning(
                    "Government login failed: "
                    "Supabase Auth rejected credentials"
                )

                return (
                    None,
                    "Invalid Employee ID or password. "
                    "If you recently registered, also make sure "
                    "your email has been verified."
                )

        # ------------------------------------------
        # LEGACY ACCOUNT FALLBACK
        # ------------------------------------------

        else:

            if not verify_password(
                password,
                user.get("password_hash")
            ):

                logger.warning(
                    "Legacy government login failed: Invalid password"
                )

                return (
                    None,
                    "Invalid Employee ID or password."
                )

        # Credentials are valid. Now enforce application access.

        if not user.get(
            "is_active",
            True
        ):

            logger.warning(
                "Government login blocked: Account disabled"
            )

            return (
                None,
                "Your account has been disabled. "
                "Please contact the administrator."
            )

        status = (
            user.get("status")
            or "approved"
        ).lower()

        if status == "pending":

            return (
                None,
                "Your account is waiting for administrator approval."
            )

        if status == "rejected":

            return (
                None,
                "Your account request was rejected. "
                "Please contact the administrator."
            )

        if status != "approved":

            return (
                None,
                "Your account is not approved for access."
            )

        return (
            {
                "id": user.get("id"),
                "auth_user_id": auth_user_id,
                "employee_id": user.get("employee_id"),
                "employee_name": user.get("employee_name"),
                "email": email,
                "department": user.get("department"),
                "role": user.get("role", "government")
            },
            "Login successful."
        )

    except Exception:

        logger.exception(
            "Government login validation failed"
        )

        return (
            None,
            "Unable to sign in at the moment. Please try again."
        )


# --------------------------------------------------
# FORGOT PASSWORD
# Supabase recovery OTP flow for Streamlit
# --------------------------------------------------

def send_password_reset_code(
    email
):

    email = email.strip().lower()

    try:

        auth_client = get_public_supabase_client()

        # Supabase sends the Reset Password email.
        # The recovery email template must display {{ .Token }}
        # so the user receives a one-time recovery code.
        auth_client.auth.reset_password_for_email(
            email
        )

        logger.info(
            "Password recovery code request submitted"
        )

        # Generic response prevents user enumeration.
        return (
            True,
            "If the email is registered, a password "
            "recovery code has been sent."
        )

    except Exception:

        logger.exception(
            "Password recovery code request failed"
        )

        return (
            False,
            "Unable to send the password recovery message."
        )


def complete_password_reset(
    email,
    recovery_code,
    new_password
):

    email = email.strip().lower()
    recovery_code = recovery_code.strip()

    try:

        auth_client = get_public_supabase_client()

        # Verify the one-time recovery code.
        verification = auth_client.auth.verify_otp(
            {
                "email": email,
                "token": recovery_code,
                "type": "recovery"
            }
        )

        if (
            not verification
            or not verification.user
            or not verification.session
        ):

            logger.warning(
                "Password recovery verification failed"
            )

            return (
                False,
                "Invalid or expired recovery code."
            )

        # verify_otp returns an authenticated recovery session.
        # Explicitly set it on this client before updating password.
        auth_client.auth.set_session(
            verification.session.access_token,
            verification.session.refresh_token
        )

        auth_client.auth.update_user(
            {
                "password": new_password
            }
        )

        # End the temporary recovery session.
        try:
            auth_client.auth.sign_out()
        except Exception:
            pass

        logger.info(
            "Government user password reset completed"
        )

        return (
            True,
            "Password updated successfully. "
            "You can now sign in with your new password."
        )

    except Exception:

        logger.exception(
            "Password recovery verification or update failed"
        )

        return (
            False,
            "Invalid or expired recovery code, or the password "
            "could not be updated. Please request a new code."
        )


# --------------------------------------------------
# ADMIN AUTHENTICATION
# --------------------------------------------------

def validate_admin(
    username,
    password
):

    if not ADMIN_USERNAME or not ADMIN_PASSWORD:

        logger.error(
            "Administrator credentials are not configured"
        )

        return False

    username_ok = hmac.compare_digest(
        username.strip(),
        ADMIN_USERNAME
    )

    password_ok = hmac.compare_digest(
        password,
        ADMIN_PASSWORD
    )

    return (
        username_ok
        and password_ok
    )


# --------------------------------------------------
# ADMIN USER MANAGEMENT
# --------------------------------------------------

def get_government_users():

    try:

        service_client = get_service_supabase_client()

        response = (
            service_client
            .table("government_users")
            .select(
                "id, auth_user_id, employee_id, employee_name, "
                "email, department, status, role, is_active, "
                "created_at, approved_at, approved_by"
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        return response.data or []

    except Exception:

        logger.exception(
            "Unable to retrieve government users for admin dashboard"
        )

        return []


def set_government_user_status(
    row_id,
    status
):

    try:

        service_client = get_service_supabase_client()

        values = {
            "status": status
        }

        if status == "approved":

            values["approved_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            values["approved_by"] = (
                ADMIN_USERNAME
                or "administrator"
            )

        (
            service_client
            .table("government_users")
            .update(values)
            .eq("id", row_id)
            .execute()
        )

        logger.info(
            "Administrator changed government account status"
        )

        return True

    except Exception:

        logger.exception(
            "Administrator status update failed"
        )

        return False


def set_government_user_active(
    row_id,
    is_active
):

    try:

        service_client = get_service_supabase_client()

        (
            service_client
            .table("government_users")
            .update(
                {
                    "is_active": is_active
                }
            )
            .eq("id", row_id)
            .execute()
        )

        logger.info(
            "Administrator changed government account active state"
        )

        return True

    except Exception:

        logger.exception(
            "Administrator active-state update failed"
        )

        return False


# ==================================================
# CACHE RETRIEVER
# IMPORTANT FOR SPEED
# ==================================================

@st.cache_resource(show_spinner=False)
def get_cached_retriever(scheme):
    return get_retriever(
        scheme=scheme
    )


# ==================================================
# LOGIN PAGE - POLISHED RESPONSIVE LANDING UI
# Authentication logic is unchanged
# ==================================================

if not st.session_state.logged_in:

    st.markdown(
        """
        <style>
        /* --------------------------------------------------
           REMOVE STREAMLIT CHROME / DEPLOY UI
        -------------------------------------------------- */
        #MainMenu,
        footer,
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stAppDeployButton,
        button[kind="header"] {
            display: none !important;
            visibility: hidden !important;
        }

        html,
        body,
        [data-testid="stAppViewContainer"],
        .stApp {
            background:
                radial-gradient(circle at 10% 10%, rgba(44, 124, 255, 0.10), transparent 28%),
                radial-gradient(circle at 92% 8%, rgba(128, 75, 255, 0.10), transparent 26%),
                linear-gradient(180deg, #f7fbff 0%, #ffffff 54%, #f7faff 100%)
                !important;
            color: #183153 !important;
        }

        [data-testid="stSidebar"] {
            display: none !important;
        }

        .block-container {
            width: min(96vw, 1460px) !important;
            max-width: 1460px !important;
            margin: 0 auto !important;
            padding-top: clamp(0.8rem, 1.5vw, 1.35rem) !important;
            padding-bottom: 1.5rem !important;
            padding-left: clamp(0.7rem, 1.5vw, 1.2rem) !important;
            padding-right: clamp(0.7rem, 1.5vw, 1.2rem) !important;
        }

        /* --------------------------------------------------
           TOP BRAND BAR
        -------------------------------------------------- */
        .landing-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            padding: 14px 18px;
            margin-bottom: 14px;
            border: 1px solid #dfe9f6;
            border-radius: 18px;
            background: rgba(255,255,255,0.86);
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 30px rgba(41, 78, 125, 0.06);
        }

        .landing-brand-wrap {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }

        .landing-logo {
            width: 46px;
            height: 46px;
            border-radius: 14px;
            display: grid;
            place-items: center;
            color: white;
            font-size: 24px;
            background: linear-gradient(135deg, #1688ee, #5e55ef);
            box-shadow: 0 8px 18px rgba(55, 94, 224, 0.22);
            flex: 0 0 auto;
        }

        .landing-brand-title {
            color: #163762;
            font-size: clamp(21px, 2vw, 28px);
            font-weight: 900;
            line-height: 1.05;
            letter-spacing: -0.6px;
        }

        .landing-brand-sub {
            margin-top: 3px;
            color: #72839a;
            font-size: 12px;
            font-weight: 600;
        }

        .landing-trust {
            color: #44627f;
            font-size: 12px;
            font-weight: 700;
            padding: 8px 12px;
            border: 1px solid #dce8f5;
            border-radius: 999px;
            background: #f7fbff;
            white-space: nowrap;
        }

        /* --------------------------------------------------
           SHARED HERO CARD
        -------------------------------------------------- */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #dce7f5 !important;
            border-radius: 26px !important;
            background: rgba(255,255,255,0.96) !important;
            box-shadow: 0 18px 48px rgba(39, 74, 122, 0.10) !important;
            overflow: hidden !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: clamp(14px, 1.8vw, 22px) !important;
        }

        /* --------------------------------------------------
           LEFT MARKETING PANEL
        -------------------------------------------------- */
        .hero-kicker-login {
            display: inline-block;
            padding: 7px 12px;
            margin-bottom: 10px;
            border-radius: 999px;
            color: #0e76cc;
            background: #eaf6ff;
            border: 1px solid #d3ebff;
            font-size: 10.5px;
            font-weight: 900;
            letter-spacing: 0.65px;
        }

        .hero-title-login {
            color: #142f56 !important;
            font-size: clamp(32px, 3.4vw, 50px);
            line-height: 1.02;
            font-weight: 950;
            letter-spacing: -1.6px;
            margin-bottom: 10px;
        }

        .hero-title-login span {
            background: linear-gradient(90deg, #1288ea, #7757ea);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-copy-login {
            color: #60738e !important;
            font-size: clamp(13px, 1.15vw, 15.5px);
            line-height: 1.65;
            max-width: 660px;
            margin-bottom: 14px;
        }

        [data-testid="stImage"] {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 2px;
            margin-bottom: 8px;
        }

        [data-testid="stImage"] img {
            width: 100% !important;
            height: clamp(260px, 30vw, 430px) !important;
            max-height: 430px !important;
            object-fit: contain !important;
            object-position: center !important;
            background: linear-gradient(145deg, #061b43, #0a2e68) !important;
            border-radius: 20px !important;
            border: 1px solid rgba(198, 218, 242, 0.95);
            box-shadow: 0 14px 34px rgba(28, 70, 130, 0.13);
        }

        .benefit-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0,1fr));
            gap: 8px;
            margin-top: 8px;
        }

        .benefit-chip {
            min-height: 66px;
            padding: 10px 11px;
            border-radius: 13px;
            background: linear-gradient(145deg, #fbfdff, #f2f7ff);
            border: 1px solid #dfe9f5;
        }

        .benefit-chip strong {
            display: block;
            color: #24476f;
            font-size: 12px;
            margin-bottom: 3px;
        }

        .benefit-chip span {
            display: block;
            color: #72839a;
            font-size: 10.8px;
            line-height: 1.35;
        }

        /* --------------------------------------------------
           RIGHT ACCESS PANEL
        -------------------------------------------------- */
        .access-kicker {
            color: #62748c;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .access-title {
            color: #17365f !important;
            font-size: clamp(26px, 2.4vw, 36px);
            font-weight: 900;
            line-height: 1.08;
            letter-spacing: -0.8px;
            margin-bottom: 7px;
        }

        .access-copy {
            color: #75869c !important;
            font-size: 13px;
            line-height: 1.55;
            margin-bottom: 10px;
        }

        div[data-baseweb="tab-list"] {
            width: 100% !important;
            display: grid !important;
            grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
            gap: 3px !important;
            padding: 4px !important;
            border: 1px solid #e2eaf4;
            border-radius: 13px;
            background: #f7faff;
        }

        button[data-baseweb="tab"] {
            min-width: 0 !important;
            padding: 8px 5px !important;
            border-radius: 9px !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: #ffffff !important;
            box-shadow: 0 3px 10px rgba(43, 75, 118, 0.08);
        }

        button[data-baseweb="tab"] p {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            text-align: center !important;
            line-height: 1.15 !important;
            font-size: clamp(9.6px, 0.9vw, 12px) !important;
            font-weight: 750 !important;
        }

        [data-testid="stTextInput"] label p {
            color: #29415f !important;
            font-size: 12px !important;
            font-weight: 750 !important;
        }

        .stTextInput input {
            min-height: 43px !important;
            border-radius: 10px !important;
            border: 1px solid #d7e2ee !important;
            background: #ffffff !important;
            color: #1b304d !important;
            font-size: 13.5px !important;
        }

        .stTextInput input:focus {
            border-color: #4c80e8 !important;
            box-shadow: 0 0 0 3px rgba(76, 128, 232, 0.08) !important;
        }

        .stButton > button {
            min-height: 44px !important;
            border-radius: 10px !important;
            font-size: 13.5px !important;
            font-weight: 800 !important;
            transition: transform 0.16s ease, box-shadow 0.16s ease !important;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
        }

        .stButton > button[kind="primary"] {
            color: #ffffff !important;
            border: none !important;
            background: linear-gradient(90deg, #0f8de8, #345ce6, #744be8) !important;
            box-shadow: 0 9px 20px rgba(55, 85, 224, 0.20) !important;
        }

        [data-testid="stAlert"] {
            border-radius: 11px !important;
            font-size: 12px !important;
        }

        details {
            border: 1px solid #dee7f2 !important;
            border-radius: 11px !important;
            background: #fbfdff !important;
        }

        .login-security {
            margin-top: 10px;
            padding: 9px 10px;
            border: 1px solid #e0e8f2;
            border-radius: 11px;
            background: linear-gradient(90deg, #f8fbff, #fbf9ff);
            color: #6d7f94 !important;
            text-align: center;
            font-size: 10.5px;
            font-weight: 650;
        }

        .login-security strong {
            color: #315175 !important;
        }

        /* --------------------------------------------------
           REAL FEATURE CARDS
        -------------------------------------------------- */
        .why-title {
            margin: 18px 0 4px;
            text-align: center;
            color: #18375f;
            font-size: clamp(22px, 2.2vw, 31px);
            font-weight: 900;
            letter-spacing: -0.7px;
        }

        .why-sub {
            margin-bottom: 13px;
            text-align: center;
            color: #78899d;
            font-size: 12.5px;
        }

        .feature-grid-login {
            display: grid;
            grid-template-columns: repeat(4, minmax(0,1fr));
            gap: 12px;
        }

        .feature-login {
            min-height: 132px;
            padding: 15px;
            border-radius: 16px;
            border: 1px solid #dee8f5;
            background: #ffffff;
            box-shadow: 0 7px 22px rgba(41, 78, 125, 0.05);
        }

        .feature-login:nth-child(1) {
            background: linear-gradient(145deg,#ffffff,#f7f2ff);
        }

        .feature-login:nth-child(2) {
            background: linear-gradient(145deg,#ffffff,#f1fff5);
        }

        .feature-login:nth-child(3) {
            background: linear-gradient(145deg,#ffffff,#f1f7ff);
        }

        .feature-login:nth-child(4) {
            background: linear-gradient(145deg,#ffffff,#fff8f0);
        }

        .feature-login-icon {
            font-size: 23px;
            margin-bottom: 8px;
        }

        .feature-login-title {
            color: #24466e;
            font-size: 13.5px;
            font-weight: 850;
            margin-bottom: 5px;
        }

        .feature-login-copy {
            color: #74859a;
            font-size: 11.5px;
            line-height: 1.5;
        }

        .landing-footer {
            margin-top: 14px;
            padding: 13px 16px;
            border-radius: 15px;
            border: 1px solid #dfe8f3;
            background: linear-gradient(90deg,#f7fbff,#fbf9ff);
            color: #657990;
            text-align: center;
            font-size: 11.5px;
            line-height: 1.6;
        }

        .landing-footer strong {
            color: #274b73;
        }

        /* --------------------------------------------------
           RESPONSIVE
        -------------------------------------------------- */
        @media (max-width: 1050px) {
            .landing-trust {
                display: none;
            }

            .benefit-grid {
                grid-template-columns: 1fr;
            }

            .feature-grid-login {
                grid-template-columns: repeat(2, minmax(0,1fr));
            }

            [data-testid="stImage"] img {
                height: clamp(240px, 37vw, 350px) !important;
            }
        }

        @media (max-width: 760px) {
            .block-container {
                width: 98vw !important;
                padding-left: 0.45rem !important;
                padding-right: 0.45rem !important;
            }

            .landing-topbar {
                border-radius: 14px;
                padding: 11px 12px;
            }

            [data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 18px !important;
            }

            .hero-title-login {
                font-size: 34px;
            }

            .benefit-grid {
                grid-template-columns: repeat(3, minmax(0,1fr));
            }

            div[data-baseweb="tab-list"] {
                grid-template-columns: repeat(2, minmax(0,1fr)) !important;
            }

            .feature-grid-login {
                grid-template-columns: 1fr;
            }

            [data-testid="stImage"] img {
                height: auto !important;
                max-height: 330px !important;
                object-fit: cover !important;
            }
        }

        @media (max-width: 480px) {
            .landing-logo {
                width: 40px;
                height: 40px;
                font-size: 20px;
            }

            .landing-brand-title {
                font-size: 21px;
            }

            .landing-brand-sub {
                font-size: 10.5px;
            }

            .benefit-grid {
                grid-template-columns: 1fr;
            }

            .hero-title-login {
                font-size: 30px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="landing-topbar">
            <div class="landing-brand-wrap">
                <div class="landing-logo">🛡️</div>
                <div>
                    <div class="landing-brand-title">AI Assist</div>
                    <div class="landing-brand-sub">
                        Insurance Policy Information System
                    </div>
                </div>
            </div>
            <div class="landing-trust">
                🔐 Secure Access &nbsp; • &nbsp; 📄 Source Grounded
                &nbsp; • &nbsp; 🤖 RAG Powered
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.container(border=True):

        image_col, login_col = st.columns(
            [1.08, 0.92],
            gap="large"
        )

        # ----------------------------------------------
        # LEFT MARKETING PANEL
        # ----------------------------------------------

        with image_col:

            st.markdown(
                """
                <div class="hero-kicker-login">
                    AI-POWERED INSURANCE INTELLIGENCE
                </div>

                <div class="hero-title-login">
                    Understand insurance.<br>
                    <span>Find answers faster.</span>
                </div>

                <div class="hero-copy-login">
                    Ask natural-language questions and receive
                    clear answers grounded in the insurance
                    documents available to AI Assist.
                </div>
                """,
                unsafe_allow_html=True
            )

            if os.path.exists(LOGIN_IMAGE_PATH):

                st.image(
                    LOGIN_IMAGE_PATH,
                    use_container_width=True
                )

            else:

                st.error(
                    "Image not found: assets/ai_assist_login.png"
                )

            st.html(
                """
                <div class="benefit-grid">
                    <div class="benefit-chip">
                        <strong>🔎 Intelligent Retrieval</strong>
                        <span>Searches semantically relevant policy content.</span>
                    </div>
                    <div class="benefit-chip">
                        <strong>📄 Source Grounding</strong>
                        <span>Shows supporting document and page references.</span>
                    </div>
                    <div class="benefit-chip">
                        <strong>🔐 Controlled Access</strong>
                        <span>Separate public, employee and admin access.</span>
                    </div>
                </div>
                """
            )

        # ----------------------------------------------
        # RIGHT ACCESS PANEL
        # ----------------------------------------------

        with login_col:

            st.markdown(
                """
                <div class="access-kicker">ACCESS PORTAL</div>
                <div class="access-title">Welcome to AI Assist</div>
                <div class="access-copy">
                    Public users can explore synthetic insurance
                    information directly. Approved government
                    employees can access government scheme content.
                </div>
                """,
                unsafe_allow_html=True
            )

            (
                public_tab,
                govt_login_tab,
                govt_signup_tab,
                forgot_password_tab
            ) = st.tabs(
                [
                    "🌐 Public",
                    "🏛️ Government Login",
                    "📝 Register",
                    "🔑 Forgot Password"
                ]
            )

            # ==========================================
            # PUBLIC ACCESS
            # ==========================================

            with public_tab:

                st.info(
                    "🌐 Public access is limited to the "
                    "Synthetic Insurance knowledge base."
                )

                if st.button(
                    "🌐 Continue as Public User",
                    type="primary",
                    use_container_width=True,
                    key="public_access_button"
                ):

                    st.session_state.logged_in = True
                    st.session_state.user_role = "public"
                    st.session_state.username = "public"
                    st.session_state.user_profile = None

                    logger.info(
                        "Public user access started"
                    )

                    st.rerun()

            # ==========================================
            # GOVERNMENT LOGIN
            # ==========================================

            with govt_login_tab:

                employee_id_login = st.text_input(
                    "Government Employee ID",
                    placeholder="Enter your Employee ID",
                    key="govt_login_employee_id"
                )

                govt_login_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="govt_login_password"
                )

                govt_login_button = st.button(
                    "🏛️ Sign In",
                    type="primary",
                    use_container_width=True,
                    key="government_signin_button"
                )

                if govt_login_button:

                    government_user, message = (
                        validate_government_user(
                            employee_id_login,
                            govt_login_password
                        )
                    )

                    if government_user:

                        st.session_state.logged_in = True
                        st.session_state.user_role = "government"
                        st.session_state.username = (
                            government_user[
                                "employee_id"
                            ]
                        )
                        st.session_state.user_profile = (
                            government_user
                        )

                        logger.info(
                            "Government employee login successful"
                        )

                        st.rerun()

                    else:

                        st.error(message)

            # ==========================================
            # GOVERNMENT ACCOUNT REGISTRATION
            # ==========================================

            with govt_signup_tab:

                st.caption(
                    "New government accounts require administrator "
                    "approval before government scheme access."
                )

                govt_employee_id = st.text_input(
                    "Government Employee ID",
                    placeholder="Enter your Employee ID",
                    key="govt_employee_id"
                )

                govt_username = st.text_input(
                    "Employee Name",
                    placeholder="Enter employee name",
                    key="govt_signup_username"
                )

                govt_email = st.text_input(
                    "Official / Registered Email",
                    placeholder="name@example.com",
                    key="govt_signup_email"
                )

                govt_department = st.text_input(
                    "Department / Office",
                    placeholder="Example: Health Department",
                    key="govt_department"
                )

                govt_password = st.text_input(
                    "Create Password",
                    type="password",
                    placeholder="Create a password",
                    key="govt_signup_password"
                )

                govt_confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Re-enter password",
                    key="govt_signup_confirm_password"
                )

                create_account_button = st.button(
                    "📝 Submit Registration",
                    use_container_width=True,
                    key="create_government_account"
                )

                if create_account_button:

                    if not all(
                        [
                            govt_employee_id.strip(),
                            govt_username.strip(),
                            govt_email.strip(),
                            govt_department.strip(),
                            govt_password
                        ]
                    ):

                        logger.warning(
                            "Government registration validation "
                            "failed: Missing fields"
                        )

                        st.warning(
                            "Please complete all account fields."
                        )

                    elif (
                        "@" not in govt_email
                        or "." not in govt_email
                    ):

                        st.warning(
                            "Please enter a valid email address."
                        )

                    elif (
                        govt_password
                        != govt_confirm_password
                    ):

                        logger.warning(
                            "Government registration validation "
                            "failed: Password mismatch"
                        )

                        st.warning(
                            "Passwords do not match."
                        )

                    elif len(govt_password) < 8:

                        st.warning(
                            "Password must contain at least "
                            "8 characters."
                        )

                    else:

                        success, message = (
                            create_government_user(
                                govt_username,
                                govt_email,
                                govt_password,
                                govt_employee_id,
                                govt_department
                            )
                        )

                        if success:

                            st.success(message)

                        else:

                            st.error(message)

            # ==========================================
            # FORGOT PASSWORD
            # ==========================================

            with forgot_password_tab:

                st.caption(
                    "Enter your registered email to receive a "
                    "one-time password recovery code."
                )

                recovery_email = st.text_input(
                    "Registered Email",
                    placeholder="name@example.com",
                    key="password_recovery_email"
                )

                if st.button(
                    "📧 Send Recovery Code",
                    use_container_width=True,
                    key="send_recovery_code"
                ):

                    clean_recovery_email = (
                        recovery_email.strip().lower()
                    )

                    if not clean_recovery_email:

                        st.warning(
                            "Please enter your registered email."
                        )

                    elif (
                        "@" not in clean_recovery_email
                        or "." not in clean_recovery_email
                    ):

                        st.warning(
                            "Please enter a valid email address."
                        )

                    else:

                        success, message = (
                            send_password_reset_code(
                                clean_recovery_email
                            )
                        )

                        if success:
                            st.success(message)
                        else:
                            st.error(message)

                st.divider()

                st.caption(
                    "Enter the recovery code from your email "
                    "and create a new password."
                )

                # A form is used here so Streamlit submits all four
                # recovery values together in one request. This avoids
                # browser/autofill and rerun-related validation issues.
                with st.form(
                    "password_reset_form",
                    clear_on_submit=False
                ):

                    recovery_email_confirm = st.text_input(
                        "Email for Verification",
                        placeholder="name@example.com",
                        key="password_reset_email_confirm"
                    )

                    recovery_code = st.text_input(
                        "Recovery Code",
                        placeholder="Enter the code from the email",
                        key="password_recovery_code"
                    )

                    new_password = st.text_input(
                        "New Password",
                        type="password",
                        key="new_recovery_password"
                    )

                    confirm_new_password = st.text_input(
                        "Confirm New Password",
                        type="password",
                        key="confirm_new_recovery_password"
                    )

                    update_password_button = (
                        st.form_submit_button(
                            "🔑 Update Password",
                            type="primary",
                            use_container_width=True
                        )
                    )

                    if update_password_button:

                        clean_email = (
                            recovery_email_confirm
                            .strip()
                            .lower()
                        )

                        clean_code = (
                            recovery_code.strip()
                        )

                        if not clean_email:

                            st.warning(
                                "Please enter your registered email."
                            )

                        elif not clean_code:

                            st.warning(
                                "Please enter the recovery code "
                                "from your email."
                            )

                        elif not new_password:

                            st.warning(
                                "Please enter a new password."
                            )

                        elif not confirm_new_password:

                            st.warning(
                                "Please confirm your new password."
                            )

                        elif (
                            "@" not in clean_email
                            or "." not in clean_email
                        ):

                            st.warning(
                                "Please enter a valid email address."
                            )

                        elif (
                            new_password
                            != confirm_new_password
                        ):

                            st.warning(
                                "Passwords do not match."
                            )

                        elif len(new_password) < 8:

                            st.warning(
                                "Password must contain at least "
                                "8 characters."
                            )

                        else:

                            success, message = (
                                complete_password_reset(
                                    clean_email,
                                    clean_code,
                                    new_password
                                )
                            )

                            if success:

                                st.success(message)

                                st.info(
                                    "Password reset complete. "
                                    "Open Government Login and sign in "
                                    "with the same Employee ID and your "
                                    "new password."
                                )

                                logger.info(
                                    "Password reset form completed successfully"
                                )

                            else:

                                st.error(message)


            # ==========================================
            # ==========================================
            # ADMIN LOGIN
            # ==========================================

            with st.expander(
                "🛡️ Administrator Access",
                expanded=False
            ):

                admin_username = st.text_input(
                    "Administrator Username",
                    key="admin_login_username"
                )

                admin_password = st.text_input(
                    "Administrator Password",
                    type="password",
                    key="admin_login_password"
                )

                if st.button(
                    "🛡️ Administrator Sign In",
                    use_container_width=True,
                    key="admin_signin_button"
                ):

                    if validate_admin(
                        admin_username,
                        admin_password
                    ):

                        st.session_state.logged_in = True
                        st.session_state.user_role = "admin"
                        st.session_state.username = (
                            ADMIN_USERNAME
                        )
                        st.session_state.user_profile = None

                        logger.info(
                            "Administrator login successful"
                        )

                        st.rerun()

                    else:

                        logger.warning(
                            "Administrator login failed"
                        )

                        st.error(
                            "Invalid administrator credentials."
                        )

            st.markdown(
                """
                <div class="login-security">
                    🔒 <strong>Secure Access</strong>
                    &nbsp; • &nbsp;
                    👤 <strong>Admin Approval</strong>
                    &nbsp; • &nbsp;
                    📄 <strong>Source Grounded</strong>
                    &nbsp; • &nbsp;
                    🤖 <strong>AI Powered</strong>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.html(
        """
        <div class="why-title">Why Choose AI Assist?</div>
        <div class="why-sub">Real features implemented in this project</div>

        <div class="feature-grid-login">
            <div class="feature-login">
                <div class="feature-login-icon">🧠</div>
                <div class="feature-login-title">RAG-Based Intelligence</div>
                <div class="feature-login-copy">
                    Combines semantic retrieval with Gemini to answer
                    questions using retrieved policy context.
                </div>
            </div>
            <div class="feature-login">
                <div class="feature-login-icon">📄</div>
                <div class="feature-login-title">Source Grounding</div>
                <div class="feature-login-copy">
                    Presents supporting policy document names and page
                    references with generated answers.
                </div>
            </div>
            <div class="feature-login">
                <div class="feature-login-icon">🔐</div>
                <div class="feature-login-title">Controlled Access</div>
                <div class="feature-login-copy">
                    Supports public users, approved government employees,
                    administrator approval and account controls.
                </div>
            </div>
            <div class="feature-login">
                <div class="feature-login-icon">🔑</div>
                <div class="feature-login-title">Account Recovery</div>
                <div class="feature-login-copy">
                    Email-linked Supabase Auth accounts support secure
                    password recovery and reset.
                </div>
            </div>
        </div>

        <div class="landing-footer">
            <strong>🛡️ AI Assist</strong> • RAG-Based Insurance Policy Information System<br>
            Python • LangChain • HuggingFace • ChromaDB • Gemini • Streamlit • Supabase
        </div>
        """
    )

    st.stop()


# ==================================================
# INSIDE / SEARCH PAGE - PROFESSIONAL UI
# IMPORTANT: RAG LOGIC BELOW IS UNCHANGED
# ==================================================

st.markdown(
    """
    <style>
    /* ---------- Hide Streamlit chrome / top white gap ---------- */
    #MainMenu {display:none !important; visibility:hidden !important;}
    footer {display:none !important; visibility:hidden !important;}
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    [data-testid="stToolbar"] {display:none !important;}
    [data-testid="stDecoration"] {display:none !important;}
    [data-testid="stStatusWidget"] {display:none !important;}
    .stAppDeployButton {display:none !important;}
    button[kind="header"] {display:none !important;}

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #f7faff !important;
        color: #19304f !important;
    }

    .block-container {
        width: 96% !important;
        max-width: 1220px !important;
        margin: 0 auto !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        display: block !important;
        background:
            linear-gradient(180deg, #ffffff 0%, #f3f8ff 100%) !important;
        border-right: 1px solid #dce8f6 !important;
    }

    [data-testid="stSidebarContent"] {
        padding-top: 1.1rem !important;
    }

    [data-testid="stSidebar"] h1 {
        color: #173b70 !important;
        font-size: 30px !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px !important;
    }

    [data-testid="stSidebar"] h3 {
        color: #1d4779 !important;
        font-size: 20px !important;
        font-weight: 750 !important;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #61738b !important;
    }

    /* ---------- Hero ---------- */
    .hero-shell {
        background:
            radial-gradient(circle at 90% 15%, rgba(124, 92, 255, 0.13), transparent 30%),
            radial-gradient(circle at 72% 80%, rgba(55, 166, 255, 0.13), transparent 34%),
            linear-gradient(120deg, #eaf5ff 0%, #f4f8ff 48%, #f6efff 100%);
        border: 1px solid #d9e7f7;
        border-radius: 24px;
        padding: 24px 30px;
        box-shadow: 0 12px 32px rgba(44, 83, 132, 0.08);
        margin-bottom: 22px;
        overflow: hidden;
    }

    .hero-grid {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(200px, 260px);
        gap: 24px;
        align-items: center;
    }

    .hero-kicker {
        color: #2768d9;
        font-size: 13px;
        font-weight: 850;
        letter-spacing: 0.9px;
        margin-bottom: 8px;
    }

    .hero-title {
        color: #17345f;
        font-size: clamp(34px, 4vw, 46px);
        line-height: 1.02;
        font-weight: 900;
        letter-spacing: -1.8px;
        margin-bottom: 10px;
    }

    .hero-title span {
        background: linear-gradient(90deg, #1f64d8, #7258e8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-subtitle {
        color: #244770;
        font-size: clamp(18px, 2.2vw, 23px);
        font-weight: 800;
        margin-bottom: 14px;
    }

    .hero-copy {
        color: #5c6f89;
        font-size: clamp(14px, 1.3vw, 16px);
        line-height: 1.72;
        max-width: 720px;
    }

    .hero-visual {
        height: 145px;
        border-radius: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        background:
            linear-gradient(145deg, rgba(255,255,255,0.72), rgba(232,241,255,0.64));
        border: 1px solid rgba(255,255,255,0.88);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
        position: relative;
    }

    .hero-visual-main {
        font-size: 76px;
        filter: drop-shadow(0 8px 10px rgba(34, 76, 135, 0.16));
    }

    .hero-visual-search {
        position: absolute;
        right: 34px;
        bottom: 24px;
        font-size: 44px;
    }

    /* ---------- Feature cards ---------- */
    .feature-card {
        min-height: 155px;
        padding: 18px 20px;
        border-radius: 17px;
        border: 1px solid #dce7f4;
        background: #ffffff;
        box-shadow: 0 7px 22px rgba(42, 75, 120, 0.06);
    }

    .feature-card.blue {
        background: linear-gradient(145deg, #ffffff, #eef7ff);
    }

    .feature-card.green {
        background: linear-gradient(145deg, #ffffff, #f0fff5);
    }

    .feature-card.purple {
        background: linear-gradient(145deg, #ffffff, #f7f1ff);
    }

    .feature-icon {
        width: 43px;
        height: 43px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 16px;
        font-size: 23px;
        margin-bottom: 15px;
        box-shadow: 0 5px 13px rgba(42, 76, 125, 0.08);
        background: rgba(255,255,255,0.8);
    }

    .feature-title {
        color: #1e3d67;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .feature-copy {
        color: #61738a;
        font-size: 14.5px;
        line-height: 1.62;
    }

    /* ---------- Knowledge badge ---------- */
    .kb-strip {
        margin-top: 20px;
        background: #ffffff;
        border: 1px solid #dce7f4;
        border-radius: 16px;
        padding: 15px 18px;
        box-shadow: 0 5px 16px rgba(42, 76, 125, 0.05);
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .kb-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 6px 11px;
        background: #eaf4ff;
        color: #2364cc;
        font-size: 11px;
        font-weight: 850;
        letter-spacing: 0.55px;
        white-space: nowrap;
    }

    .kb-text {
        color: #405875;
        font-size: 14px;
        font-weight: 650;
    }

    /* ---------- Section heading ---------- */
    .section-title {
        color: #1d3b64;
        font-size: 23px;
        font-weight: 850;
        margin: 24px 0 6px 0;
    }

    .section-subtitle {
        color: #74849a;
        font-size: 14px;
        margin-bottom: 13px;
    }

    /* ---------- Question area ---------- */
    .question-shell {
        margin-top: 14px;
        background: linear-gradient(145deg, #ffffff, #fbfdff);
        border: 1px solid #dce7f4;
        border-radius: 20px;
        padding: 7px 20px 16px 20px;
        box-shadow: 0 8px 24px rgba(42, 76, 125, 0.06);
    }

    .stTextArea textarea {
        min-height: 118px !important;
        border-radius: 13px !important;
        border: 1px solid #d7e2ef !important;
        background: #ffffff !important;
        color: #203650 !important;
        font-size: 16px !important;
        box-shadow: none !important;
    }

    .stTextArea textarea:focus {
        border-color: #4a7be8 !important;
        box-shadow: 0 0 0 3px rgba(70, 115, 225, 0.08) !important;
    }

    .stButton > button {
        border-radius: 11px !important;
        min-height: 44px !important;
        font-size: 14px !important;
        font-weight: 750 !important;
        transition: all 0.18s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #1778e8, #3159df) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 7px 16px rgba(49, 89, 223, 0.18) !important;
    }

    /* ---------- Example questions ---------- */
    .sample-wrap {
        margin-top: 18px;
        background: linear-gradient(145deg, #f8fbff, #f8f5ff);
        border: 1px solid #dfe7f4;
        border-radius: 18px;
        padding: 16px 18px 7px 18px;
    }

    .sample-head {
        color: #27446e;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .sample-copy {
        color: #7a889b;
        font-size: 13px;
        margin-bottom: 8px;
    }

    /* ---------- Native alerts / answers ---------- */
    [data-testid="stAlert"] {
        border-radius: 13px !important;
        border: 1px solid #dae5f2 !important;
    }

    /* ---------- Select box ---------- */
    [data-baseweb="select"] > div {
        border-radius: 11px !important;
        border-color: #d9e4f1 !important;
        background: white !important;
    }

    /* ---------- Footer ---------- */
    .app-footer {
        color: #8795a7;
        font-size: 12px;
        text-align: center;
        padding: 22px 0 4px 0;
    }

    /* ---------- Responsive ---------- */
    @media (max-width: 1000px) {
        .hero-grid {
            grid-template-columns: minmax(0, 1fr) 210px;
        }
    }

    @media (max-width: 900px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }

        .hero-visual {
            display: none;
        }

        .hero-title {
            font-size: 36px;
        }
    }

    @media (max-width: 650px) {
        .block-container {
            width: 98% !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }

        .hero-shell {
            padding: 18px !important;
            border-radius: 18px !important;
        }

        .hero-title {
            font-size: 31px;
        }

        .hero-subtitle {
            font-size: 18px;
        }

        .feature-card {
            min-height: auto;
        }

        .kb-strip {
            flex-wrap: wrap;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.markdown(
        """
        <div style="font-size:30px;font-weight:900;color:#173b70;
                    letter-spacing:-0.6px;margin-bottom:2px;">
            🛡️ AI Assist
        </div>
        <div style="font-size:13px;color:#8090a5;margin-bottom:17px;">
            Insurance Policy Information System
        </div>
        <div style="font-size:14px;color:#657890;line-height:1.65;">
            AI-powered assistance for searching and understanding
            insurance policy documents.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    admin_workspace = "RAG Assistant"

    if st.session_state.user_role == "admin":

        admin_workspace = st.selectbox(
            "🛡️ Administrator Workspace",
            [
                "RAG Assistant",
                "User Administration"
            ]
        )

        st.divider()

    st.subheader("📚 Choose Knowledge Base")

    # Public users can access only the synthetic
    # insurance knowledge base.
    if st.session_state.user_role == "public":

        scheme_options = [
            "Synthetic Insurance"
        ]

    else:

        # Government users can access both collections.
        scheme_options = [
            "Synthetic Insurance",
            "Tamil Nadu NHIS 2026"
        ]


    scheme_option = st.selectbox(
        "Select policy collection",
        scheme_options
    )

    if scheme_option == "Synthetic Insurance":

        selected_scheme = "generic_insurance"

        st.info(
            "📘 Search health, motor, life, travel, "
            "home and other synthetic insurance documents."
        )

    else:

        selected_scheme = "TN_NHIS_2026"

        st.info(
            "🏛️ Search the Tamil Nadu New Health "
            "Insurance Scheme 2026 document."
        )

    st.divider()

    st.subheader("⚙️ Technology")

    tech_col1, tech_col2 = st.columns(2)

    with tech_col1:
        st.caption("🔎 Semantic Retrieval")
        st.caption("🧠 HuggingFace")

    with tech_col2:
        st.caption("🗃️ ChromaDB")
        st.caption("🤖 Gemini LLM")

    st.caption("🔗 LangChain orchestration")

    st.divider()

    st.caption(
        "📄 Answers are grounded in the selected policy documents."
    )

    st.divider()

    role_labels = {
        "public": "🌐 Public User",
        "government": "🏛️ Government User",
        "admin": "🛡️ Administrator"
    }

    st.caption(
        f"Signed in as: "
        f"{role_labels.get(st.session_state.user_role, 'User')}"
    )

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        logger.info(
            "User logged out | role=%s",
            st.session_state.user_role
        )

        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_profile = None
        st.rerun()


# ==================================================
# ADMIN USER MANAGEMENT DASHBOARD
# ==================================================

if (
    st.session_state.user_role == "admin"
    and admin_workspace == "User Administration"
):

    st.title(
        "🛡️ Government User Administration"
    )

    st.caption(
        "Review registrations, approve or reject access, "
        "and enable or disable government user accounts."
    )

    st.divider()

    government_users = get_government_users()

    pending_count = sum(
        1
        for user in government_users
        if (
            user.get("status")
            or "approved"
        ).lower() == "pending"
    )

    approved_count = sum(
        1
        for user in government_users
        if (
            user.get("status")
            or "approved"
        ).lower() == "approved"
    )

    disabled_count = sum(
        1
        for user in government_users
        if not user.get(
            "is_active",
            True
        )
    )

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric(
        "Pending Approval",
        pending_count
    )

    metric2.metric(
        "Approved Users",
        approved_count
    )

    metric3.metric(
        "Disabled Accounts",
        disabled_count
    )

    st.divider()

    status_filter = st.selectbox(
        "Filter accounts",
        [
            "All",
            "Pending",
            "Approved",
            "Rejected",
            "Disabled"
        ]
    )

    filtered_users = []

    for user in government_users:

        status = (
            user.get("status")
            or "approved"
        ).lower()

        is_active = user.get(
            "is_active",
            True
        )

        if status_filter == "All":
            filtered_users.append(user)

        elif (
            status_filter == "Pending"
            and status == "pending"
        ):
            filtered_users.append(user)

        elif (
            status_filter == "Approved"
            and status == "approved"
        ):
            filtered_users.append(user)

        elif (
            status_filter == "Rejected"
            and status == "rejected"
        ):
            filtered_users.append(user)

        elif (
            status_filter == "Disabled"
            and not is_active
        ):
            filtered_users.append(user)


    if not filtered_users:

        st.info(
            "No government user accounts match this filter."
        )


    for user in filtered_users:

        row_id = user.get("id")

        employee_name = (
            user.get("employee_name")
            or "Unknown Employee"
        )

        employee_id = (
            user.get("employee_id")
            or "-"
        )

        email = (
            user.get("email")
            or "Legacy account – email not linked"
        )

        department = (
            user.get("department")
            or "-"
        )

        status = (
            user.get("status")
            or "approved"
        ).lower()

        is_active = user.get(
            "is_active",
            True
        )

        status_icon = {
            "pending": "🟡",
            "approved": "🟢",
            "rejected": "🔴"
        }.get(
            status,
            "⚪"
        )

        with st.expander(
            f"{status_icon} {employee_name} • {employee_id}",
            expanded=(
                status == "pending"
            )
        ):

            st.write(
                f"**Email:** {email}"
            )

            st.write(
                f"**Department:** {department}"
            )

            st.write(
                f"**Status:** {status.title()}"
            )

            st.write(
                "**Account:** "
                + (
                    "Active"
                    if is_active
                    else "Disabled"
                )
            )

            action1, action2, action3 = st.columns(3)

            with action1:

                if st.button(
                    "✅ Approve",
                    key=f"approve_{row_id}",
                    use_container_width=True
                ):

                    if set_government_user_status(
                        row_id,
                        "approved"
                    ):

                        st.success(
                            "Account approved."
                        )

                        st.rerun()

            with action2:

                if st.button(
                    "❌ Reject",
                    key=f"reject_{row_id}",
                    use_container_width=True
                ):

                    if set_government_user_status(
                        row_id,
                        "rejected"
                    ):

                        st.success(
                            "Account rejected."
                        )

                        st.rerun()

            with action3:

                if is_active:

                    if st.button(
                        "⛔ Disable",
                        key=f"disable_{row_id}",
                        use_container_width=True
                    ):

                        if set_government_user_active(
                            row_id,
                            False
                        ):

                            st.success(
                                "Account disabled."
                            )

                            st.rerun()

                else:

                    if st.button(
                        "♻️ Enable",
                        key=f"enable_{row_id}",
                        use_container_width=True
                    ):

                        if set_government_user_active(
                            row_id,
                            True
                        ):

                            st.success(
                                "Account enabled."
                            )

                            st.rerun()


    st.stop()


# ==================================================
# HERO
# ==================================================

st.html(
    """
    <div class="hero-shell">
        <div class="hero-grid">
            <div>
                <div class="hero-kicker">
                    AI-POWERED INSURANCE INTELLIGENCE
                </div>

                <div class="hero-title">
                    AI <span>Assist</span>
                </div>

                <div class="hero-subtitle">
                    Insurance Policy Information System
                </div>

                <div class="hero-copy">
                    Ask questions about insurance policies in natural language
                    and receive intelligent answers grounded in the selected
                    policy documents.
                </div>
            </div>

            <div class="hero-visual">
                <div class="hero-visual-main">🛡️📋</div>
                <div class="hero-visual-search">🔍</div>
            </div>
        </div>
    </div>
    """
)


# ==================================================
# FEATURE CARDS
# ==================================================

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.html(
        """
        <div class="feature-card blue">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">Intelligent Search</div>
            <div class="feature-copy">
                Finds relevant policy information using semantic
                similarity for accurate results beyond exact keywords.
            </div>
        </div>
        """
    )

with col2:
    st.html(
        """
        <div class="feature-card green">
            <div class="feature-icon">🤖</div>
            <div class="feature-title">AI-Powered Answers</div>
            <div class="feature-copy">
                Generates clear answers from the relevant policy
                information returned by the retrieval system.
            </div>
        </div>
        """
    )

with col3:
    st.html(
        """
        <div class="feature-card purple">
            <div class="feature-icon">📄</div>
            <div class="feature-title">Source Grounding</div>
            <div class="feature-copy">
                Displays the document and page used to support
                each generated insurance-policy answer.
            </div>
        </div>
        """
    )


# ==================================================
# CURRENT KNOWLEDGE BASE
# ==================================================

if scheme_option == "Synthetic Insurance":
    kb_name = "🗂️ Synthetic Multi-Policy Insurance Collection"
else:
    kb_name = "🏛️ Tamil Nadu New Health Insurance Scheme 2026"

st.html(
    f"""
    <div class="kb-strip">
        <span class="kb-badge">CURRENT KNOWLEDGE BASE</span>
        <span class="kb-text">{kb_name}</span>
    </div>
    """
)


# ==================================================
# SAMPLE QUESTIONS
# ==================================================

st.html(
    """
    <div class="sample-wrap">
        <div class="sample-head">💡 Sample Questions</div>
        <div class="sample-copy">
            Choose a sample to place it directly into the question box.
        </div>
    </div>
    """
)

if scheme_option == "Synthetic Insurance":

    sample_questions = [
        "📋 What documents are required for an insurance claim?",
        "🚗 What does motor insurance cover?",
        "🏥 What benefits are available under health insurance?",
        "✈️ What happens if checked baggage is lost?",
        "🦷 Is dental treatment covered under the health policy?",
        "💰 What is the death benefit in the life insurance policy?"
    ]

else:

    sample_questions = [
        "💰 What is the maximum medical assistance available?",
        "📋 What documents are required for reimbursement?",
        "🏥 What happens for treatment in a non-network hospital?",
        "🩺 What medical treatments are covered under the scheme?",
        "📄 What are the important claim conditions?",
        "👨‍👩‍👧 Who is eligible under the Tamil Nadu NHIS 2026 scheme?"
    ]


sample_cols = st.columns(3, gap="small")

for index, sample in enumerate(sample_questions):

    with sample_cols[index % 3]:

        if st.button(
            sample,
            key=f"sample_question_{selected_scheme}_{index}",
            use_container_width=True
        ):
            # Remove the leading emoji from the text placed in the input.
            clean_sample = sample.split(" ", 1)[1] if " " in sample else sample
            st.session_state["policy_question_input"] = clean_sample
            st.rerun()


# ==================================================
# QUESTION INPUT
# ==================================================

st.html(
    """
    <div class="section-title">💬 Ask About an Insurance Policy</div>
    <div class="section-subtitle">
        Ask in natural language. AI Assist will search the selected
        knowledge base and use the most relevant policy content.
    </div>
    """
)

question = st.text_area(
    "Question",
    placeholder="Type your insurance question here...",
    height=120,
    label_visibility="collapsed",
    key="policy_question_input"
)

ask_button = st.button(
    "🔍 Get Policy Information",
    type="primary",
    use_container_width=True
)


# ==================================================
# PROCESS QUESTION
# KEEP THIS FLOW FOR SPEED - WORKING LOGIC PRESERVED
# ==================================================

if ask_button:

    if not question.strip():

        logger.warning("Question submission rejected: Empty question")

        st.warning(
            "Please enter an insurance-related question."
        )

    else:

        try:

            logger.info(
                "Policy query processing started | scheme=%s",
                selected_scheme
            )

            # ------------------------------------------
            # RETRIEVAL
            # ------------------------------------------

            with st.spinner(
                "🔍 Preparing AI and searching policy documents..."
            ):

                retriever = get_cached_retriever(
                    selected_scheme
                )

                documents = retriever.invoke(
                    question
                )

                logger.info(
                    "Document retrieval completed | scheme=%s | documents=%d",
                    selected_scheme,
                    len(documents)
                )


            # ------------------------------------------
            # ANSWER
            # ------------------------------------------

            st.divider()

            st.subheader(
                "🤖 AI-Generated Answer"
            )

            answer_stream = stream_answer(
                question,
                documents
            )

            st.write_stream(
                answer_stream
            )

            logger.info(
                "RAG answer generated successfully | scheme=%s",
                selected_scheme
            )


            # ------------------------------------------
            # SOURCES
            # ------------------------------------------

            st.subheader(
                "📚 Supporting Sources"
            )

            displayed_sources = set()

            for doc in documents:

                source = doc.metadata.get(
                    "source",
                    "Unknown"
                )

                page = doc.metadata.get(
                    "page_label"
                )

                if page is None:

                    raw_page = doc.metadata.get(
                        "page"
                    )

                    if isinstance(raw_page, int):
                        page = raw_page + 1
                    else:
                        page = "Unknown"

                filename = os.path.basename(
                    source
                )

                source_key = (
                    f"{filename}-{page}"
                )

                if source_key not in displayed_sources:

                    st.info(
                        f"📄 {filename} | Page {page}"
                    )

                    displayed_sources.add(
                        source_key
                    )


        except Exception as error:

            logger.exception(
                "RAG question processing failed | scheme=%s",
                selected_scheme
            )

            st.error(
                f"Unable to process your question: {error}"
            )


# ==================================================
# FOOTER
# ==================================================

st.html(
    """
    <div class="app-footer">
        🛡️ AI Assist • Retrieval-Augmented Generation for Insurance Policy Understanding
    </div>
    """
)