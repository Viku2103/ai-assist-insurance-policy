import os
import sqlite3
import hashlib
import streamlit as st

from src.generation.rag_chain import stream_answer
from src.retrieval.retriever import get_retriever


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


USER_DB_PATH = os.path.join(
    BASE_DIR,
    "users.db"
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


# ==================================================
# USER DATABASE
# Government employee accounts only
# ==================================================

def get_user_db_connection():
    connection = sqlite3.connect(USER_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def initialize_user_database():

    connection = get_user_db_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            employee_id TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'government'
        )
        """
    )

    connection.commit()
    connection.close()


def create_government_user(
    username,
    password,
    employee_id,
    department
):

    connection = get_user_db_connection()

    try:

        connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                employee_id,
                department,
                role
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username.strip(),
                hash_password(password),
                employee_id.strip(),
                department.strip(),
                "government"
            )
        )

        connection.commit()
        return True, "Government account created successfully."

    except sqlite3.IntegrityError:

        return (
            False,
            "Username or Employee ID already exists."
        )

    finally:

        connection.close()


def validate_government_user(
    employee_id,
    password
):

    connection = get_user_db_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE employee_id = ?
          AND password_hash = ?
        """,
        (
            employee_id.strip(),
            hash_password(password)
        )
    ).fetchone()

    connection.close()

    return user


initialize_user_database()


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
# LOGIN PAGE
# ==================================================

if not st.session_state.logged_in:

    st.markdown(
        """
        <style>

        html,
        body,
        [data-testid="stAppViewContainer"],
        .stApp {
            background: #ffffff !important;
        }

        [data-testid="stSidebar"] {
            display: none !important;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        .block-container {
            max-width: 1320px !important;
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }

        [data-testid="stImage"] {
            display: flex;
            justify-content: center;
            align-items: center;
            padding-top: 10px;
        }

        [data-testid="stImage"] img {
            width: 100% !important;
            max-height: 520px !important;
            object-fit: contain !important;
            border-radius: 18px !important;

            box-shadow:
                0 12px 35px
                rgba(25,70,120,0.10);
        }

        .login-brand {
            display: inline-block;
            padding: 7px 14px;
            border-radius: 999px;

            background: #eaf5ff;
            border: 1px solid #d3eaff;

            color: #0878d1;

            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;

            margin-bottom: 13px;
        }

        .login-title {
            color: #142b4d !important;
            font-size: 34px;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 6px;
        }

        .login-subtitle {
            color: #687b94 !important;
            font-size: 14px;
            line-height: 1.55;
            max-width: 430px;
            margin-bottom: 11px;
        }

        [data-testid="stTextInput"] label,
        [data-testid="stTextInput"] label p {
            color: #263a56 !important;
            font-size: 13px !important;
            font-weight: 650 !important;
        }

        .stTextInput input {
            min-height: 46px !important;
            border-radius: 10px !important;

            background: #ffffff !important;
            color: #1c304d !important;

            border:
                1px solid #d4deea !important;

            font-size: 14px !important;
        }

        .stTextInput input::placeholder {
            color: #97a6b8 !important;
        }

        .stButton > button {
            min-height: 46px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 700;
        }

        .stButton > button[kind="primary"] {
            background:
                linear-gradient(
                    90deg,
                    #078be8,
                    #315ce8
                ) !important;

            color: white !important;
            border: none !important;
        }

        .demo-login {
            margin-top: 9px;
            padding: 9px;

            border-radius: 9px;

            background: #f3f8ff;
            border: 1px solid #e0ecfb;

            color: #77879b !important;
            text-align: center;
            font-size: 11px;
        }

        .demo-login strong {
            color: #0878d1 !important;
        }

        .login-security {
            margin-top: 9px;
            padding: 9px;

            border-radius: 9px;

            background: #f8fafc;
            border: 1px solid #e3e9f0;

            color: #77879b !important;
            text-align: center;
            font-size: 11px;
        }

        .login-security strong {
            color: #334c6c !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


    image_col, login_col = st.columns(
        [1.15, 0.85],
        gap="large"
    )


    # ----------------------------------------------
    # LEFT IMAGE
    # ----------------------------------------------

    with image_col:

        if os.path.exists(LOGIN_IMAGE_PATH):

            st.image(
                LOGIN_IMAGE_PATH,
                use_container_width=True
            )

        else:

            st.error(
                "Image not found: assets/ai_assist_login.png"
            )


    # ----------------------------------------------
    # RIGHT LOGIN
    # ----------------------------------------------

    with login_col:

        st.markdown(
            "<div style='height:10px'></div>",
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="login-brand">
                🛡️ AI-POWERED INSURANCE INTELLIGENCE
            </div>

            <div class="login-title">
                Welcome to AI Assist
            </div>

            <div class="login-subtitle">
                Public users can continue directly to the synthetic
                insurance knowledge base. Government employees can
                create an account using their Employee ID and use the
                same Employee ID to sign in later.
            </div>
            """,
            unsafe_allow_html=True
        )

        public_tab, govt_login_tab, govt_signup_tab = st.tabs(
            [
                "🌐 Public Access",
                "🏛️ Government Login",
                "📝 Create Government Account"
            ]
        )

        # ==========================================
        # PUBLIC ACCESS
        # ==========================================

        with public_tab:

            st.caption(
                "Public access is limited to the Synthetic "
                "Insurance knowledge base."
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
                st.rerun()

        # ==========================================
        # GOVERNMENT EMPLOYEE LOGIN
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

                government_user = validate_government_user(
                    employee_id_login,
                    govt_login_password
                )

                if government_user:

                    st.session_state.logged_in = True
                    st.session_state.user_role = "government"
                    st.session_state.username = government_user[
                        "employee_id"
                    ]
                    st.rerun()

                else:

                    st.error(
                        "Invalid Employee ID or password."
                    )

        # ==========================================
        # GOVERNMENT EMPLOYEE ACCOUNT CREATION
        # ==========================================

        with govt_signup_tab:

            st.caption(
                "Create your government employee account once. "
                "After registration, use your Employee ID and "
                "password in the Government Login tab."
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
                "📝 Create Employee Account",
                use_container_width=True,
                key="create_government_account"
            )

            if create_account_button:

                if not all(
                    [
                        govt_employee_id.strip(),
                        govt_username.strip(),
                        govt_department.strip(),
                        govt_password
                    ]
                ):

                    st.warning(
                        "Please complete all account fields."
                    )

                elif govt_password != govt_confirm_password:

                    st.warning(
                        "Passwords do not match."
                    )

                elif len(govt_password) < 6:

                    st.warning(
                        "Password must contain at least 6 characters."
                    )

                else:

                    success, message = create_government_user(
                        govt_username,
                        govt_password,
                        govt_employee_id,
                        govt_department
                    )

                    if success:

                        st.success(
                            "Account created successfully. "
                            "You can now sign in using your "
                            "Employee ID and password."
                        )

                    else:

                        st.error(message)

        st.markdown(
            """
            <div class="login-security">
                🔒 <strong>Secure Access</strong>
                &nbsp; • &nbsp;
                📄 <strong>Source Grounded</strong>
                &nbsp; • &nbsp;
                🤖 <strong>AI Powered</strong>
            </div>
            """,
            unsafe_allow_html=True
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
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header[data-testid="stHeader"] {
        display: none !important;
        height: 0 !important;
    }
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: #f7faff !important;
        color: #19304f !important;
    }

    .block-container {
        max-width: 1220px !important;
        padding-top: 1.15rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.6rem !important;
        padding-right: 1.6rem !important;
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
        grid-template-columns: 1fr 280px;
        gap: 28px;
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
        font-size: 46px;
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
        font-size: 23px;
        font-weight: 800;
        margin-bottom: 14px;
    }

    .hero-copy {
        color: #5c6f89;
        font-size: 16px;
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
    @media (max-width: 900px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }
        .hero-visual {
            display: none;
        }
        .hero-title {
            font-size: 44px;
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

    st.subheader("📚 Choose Knowledge Base")

    # Public users can access only the synthetic
    # insurance knowledge base.
    if st.session_state.user_role == "public":

        scheme_options = [
            "Synthetic Insurance"
        ]

    else:

        # Government users and the existing admin
        # can access both collections.
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

        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.rerun()


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

        st.warning(
            "Please enter an insurance-related question."
        )

    else:

        try:

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