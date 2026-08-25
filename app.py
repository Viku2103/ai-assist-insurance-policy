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
# UI STYLING
# ==================================================

st.markdown(
    """
    <style>

    .stApp {
        background: linear-gradient(
            135deg,
            #f8fbff 0%,
            #eef5ff 50%,
            #f8fbff 100%
        );
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
        background-color: #f1f6fc;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 30px !important;
    }

    .stTextArea textarea {
        font-size: 17px !important;
        border-radius: 12px !important;
        min-height: 120px;
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
# CACHE RETRIEVER
# ==================================================

@st.cache_resource(show_spinner=False)
def get_cached_retriever(scheme):
    return get_retriever(
        scheme=scheme
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
        "Answers are grounded in the selected policy documents."
    )


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
# ==================================================

if ask_button:

    if not question.strip():

        st.warning(
            "Please enter an insurance-related question."
        )

    else:

        try:

            # ==========================================
            # FIRST-TIME MODEL / RETRIEVER LOAD
            # ==========================================

            with st.spinner(
                "⚙️ Preparing AI model and searching policy documents..."
            ):

                retriever = get_cached_retriever(
                    selected_scheme
                )

                documents = retriever.invoke(
                    question
                )


            # ==========================================
            # ANSWER
            # ==========================================

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


            # ==========================================
            # SOURCES
            # ==========================================

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
                    "page_label",
                    "Unknown"
                )

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