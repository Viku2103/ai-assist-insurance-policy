import os
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


# ==================================================
# SESSION STATE
# ==================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


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
            margin-bottom: 8px;
        }

        .login-subtitle {
            color: #687b94 !important;
            font-size: 14px;
            line-height: 1.55;
            max-width: 430px;
            margin-bottom: 15px;
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
            "<div style='height:30px'></div>",
            unsafe_allow_html=True
        )


        st.markdown(
            """
            <div class="login-brand">
                🛡️ AI-POWERED INSURANCE INTELLIGENCE
            </div>

            <div class="login-title">
                Welcome Back
            </div>

            <div class="login-subtitle">
                Sign in to AI Assist to search insurance
                policy documents and receive intelligent,
                document-grounded answers.
            </div>
            """,
            unsafe_allow_html=True
        )


        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username"
        )


        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )


        login_button = st.button(
            "🔐 Sign In",
            type="primary",
            use_container_width=True
        )


        if login_button:

            if (
                username == "admin"
                and password == "admin123"
            ):

                st.session_state.logged_in = True
                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )


        st.markdown(
            """
            <div class="demo-login">
                Demo Login:
                <strong>admin</strong>
                /
                <strong>admin123</strong>
            </div>

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
# INSIDE / SEARCH PAGE CSS
# RESTORED TO OLD CLEAN WHITE UI
# ==================================================

st.markdown(
    """
    <style>

    html,
    body,
    [data-testid="stAppViewContainer"],
    .stApp {
        background:
            linear-gradient(
                135deg,
                #f8fbff 0%,
                #eef5ff 50%,
                #f8fbff 100%
            ) !important;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1 {
        font-size: 44px !important;
        font-weight: 750 !important;
        letter-spacing: -0.5px;
    }

    h2 {
        font-size: 28px !important;
        font-weight: 700 !important;
    }

    h3 {
        font-size: 21px !important;
        font-weight: 650 !important;
    }

    p {
        font-size: 16px;
        line-height: 1.65;
    }

    [data-testid="stSidebar"] {
        display: block !important;
        background-color: #f1f6fc !important;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 30px !important;
    }

    [data-testid="stSidebar"] * {
        color: inherit;
    }

    .stTextArea textarea {
        font-size: 17px !important;
        border-radius: 12px !important;
        min-height: 120px;
        background: white !important;
        color: #1f2937 !important;
    }

    [data-baseweb="select"] > div {
        border-radius: 10px;
    }

    .stButton > button {
        height: 52px;
        border-radius: 12px;
        font-size: 17px;
        font-weight: 650;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
        font-size: 16px;
    }

    hr {
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.title("🛡️ AI Assist")

    st.caption(
        "Insurance Policy Information System"
    )

    st.write(
        "AI-powered assistance for searching "
        "and understanding insurance policy documents."
    )

    st.divider()


    # ----------------------------------------------
    # KNOWLEDGE BASE
    # ----------------------------------------------

    st.subheader(
        "📚 Choose Knowledge Base"
    )


    scheme_option = st.selectbox(
        "Select policy collection",
        [
            "Synthetic Insurance",
            "Tamil Nadu NHIS 2026"
        ]
    )


    if scheme_option == "Synthetic Insurance":

        selected_scheme = "generic_insurance"

        st.info(
            "Search health, motor, life, travel, "
            "home and other synthetic insurance documents."
        )

    else:

        selected_scheme = "TN_NHIS_2026"

        st.info(
            "Search the Tamil Nadu New Health "
            "Insurance Scheme 2026 document."
        )


    st.divider()


    # ----------------------------------------------
    # TECHNOLOGY
    # ----------------------------------------------

    st.subheader(
        "⚙️ Technology"
    )

    st.write("🔎 Semantic Retrieval")
    st.write("🧠 HuggingFace Embeddings")
    st.write("🗃️ ChromaDB")
    st.write("🤖 Gemini LLM")
    st.write("🔗 LangChain")


    st.divider()


    st.caption(
        "Answers are grounded in the selected "
        "policy documents."
    )


    st.divider()


    # ----------------------------------------------
    # LOGOUT
    # ----------------------------------------------

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.rerun()


# ==================================================
# MAIN HEADER
# ==================================================

st.title(
    "🛡️ AI Assist"
)

st.subheader(
    "Insurance Policy Information System"
)

st.write(
    """
    Ask questions about insurance policies in natural language
    and receive intelligent answers grounded in the selected
    policy documents.
    """
)

st.divider()


# ==================================================
# FEATURES
# ==================================================

col1, col2, col3 = st.columns(3)


with col1:

    st.subheader(
        "🔍 Intelligent Search"
    )

    st.write(
        "Finds relevant policy information using "
        "semantic similarity."
    )


with col2:

    st.subheader(
        "🤖 AI-Powered Answers"
    )

    st.write(
        "Generates clear answers from the retrieved "
        "policy information."
    )


with col3:

    st.subheader(
        "📄 Source Grounding"
    )

    st.write(
        "Displays the document and page used "
        "to support the answer."
    )


st.divider()


# ==================================================
# CURRENT KNOWLEDGE BASE
# ==================================================

st.subheader(
    "📚 Current Knowledge Base"
)


if scheme_option == "Synthetic Insurance":

    st.success(
        "🗂️ Synthetic Multi-Policy Insurance Collection"
    )

else:

    st.success(
        "🏛️ Tamil Nadu New Health Insurance Scheme 2026"
    )


# ==================================================
# EXAMPLE QUESTIONS
# ==================================================

st.subheader(
    "💡 Example Questions"
)


if scheme_option == "Synthetic Insurance":

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(
            "📋 What documents are required "
            "for an insurance claim?"
        )

    with col2:
        st.info(
            "🚗 What does motor insurance cover?"
        )

    with col3:
        st.info(
            "🏥 What benefits are available "
            "under health insurance?"
        )

else:

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(
            "💰 What is the maximum medical "
            "assistance available?"
        )

    with col2:
        st.info(
            "📋 What documents are required "
            "for reimbursement?"
        )

    with col3:
        st.info(
            "🏥 What happens for treatment "
            "in a non-network hospital?"
        )


# ==================================================
# QUESTION INPUT
# ==================================================

st.subheader(
    "💬 Ask About Your Insurance Policy"
)


question = st.text_area(
    "Question",
    placeholder="Type your insurance question here...",
    height=120,
    label_visibility="collapsed"
)


ask_button = st.button(
    "✨ Get Policy Information",
    type="primary",
    use_container_width=True
)


# ==================================================
# PROCESS QUESTION
# KEEP THIS FLOW FOR SPEED
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

st.divider()

st.caption(
    "🛡️ AI Assist – Insurance Policy Information System"
)

st.caption(
    "Retrieval-Augmented Generation for "
    "Insurance Policy Understanding"
)