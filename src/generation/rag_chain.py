import time
from functools import lru_cache

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from src.retrieval.retriever import get_retriever


load_dotenv()


# ==================================================
# LLM
# ==================================================

@lru_cache(maxsize=1)
def get_llm():

    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite"
    )


# ==================================================
# PROMPT
# ==================================================

def create_prompt(question, documents):

    context = "\n\n".join(
        doc.page_content for doc in documents
    )

    return f"""
You are AI Assist, an insurance policy information assistant.

Answer the user's question using ONLY the information
provided in the policy context below.

Give a clear and concise answer.

Do not invent policy information.

If the answer is not available in the context, say:
"I could not find this information in the selected policy documents."

Context:
{context}

Question:
{question}

Answer:
"""


# ==================================================
# EXTRACT RESPONSE TEXT
# ==================================================

def extract_text(content):

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text = ""

        for item in content:

            if isinstance(item, dict):
                text += item.get("text", "")

            elif isinstance(item, str):
                text += item

        return text

    return str(content)


# ==================================================
# NORMAL RAG ANSWER + TIMING
# ==================================================

def ask_question(
    question,
    scheme=None,
    retriever=None
):

    total_start = time.time()


    # ----------------------------------------------
    # RETRIEVER INITIALIZATION
    # ----------------------------------------------

    init_start = time.time()

    if retriever is None:

        retriever = get_retriever(
            scheme=scheme
        )

    init_time = time.time() - init_start


    # ----------------------------------------------
    # RETRIEVAL
    # ----------------------------------------------

    retrieval_start = time.time()

    documents = retriever.invoke(
        question
    )

    retrieval_time = (
        time.time() - retrieval_start
    )


    # ----------------------------------------------
    # PROMPT
    # ----------------------------------------------

    prompt_start = time.time()

    prompt = create_prompt(
        question,
        documents
    )

    prompt_time = (
        time.time() - prompt_start
    )


    # ----------------------------------------------
    # GEMINI
    # ----------------------------------------------

    llm = get_llm()

    gemini_start = time.time()

    response = llm.invoke(
        prompt
    )

    gemini_time = (
        time.time() - gemini_start
    )


    # ----------------------------------------------
    # RESPONSE PROCESSING
    # ----------------------------------------------

    answer = extract_text(
        response.content
    )


    # ----------------------------------------------
    # TOTAL TIME
    # ----------------------------------------------

    total_time = (
        time.time() - total_start
    )


    print("\n==============================")
    print("PERFORMANCE")
    print("==============================")

    print(
        f"Retriever initialization: "
        f"{init_time:.2f} seconds"
    )

    print(
        f"Retrieval time: "
        f"{retrieval_time:.2f} seconds"
    )

    print(
        f"Prompt creation: "
        f"{prompt_time:.2f} seconds"
    )

    print(
        f"Gemini time: "
        f"{gemini_time:.2f} seconds"
    )

    print(
        f"Total time: "
        f"{total_time:.2f} seconds"
    )

    print("==============================\n")


    return answer, documents


# ==================================================
# STREAMING VERSION
# ==================================================

def stream_answer(
    question,
    documents
):

    prompt = create_prompt(
        question,
        documents
    )

    llm = get_llm()

    for chunk in llm.stream(
        prompt
    ):

        text = extract_text(
            chunk.content
        )

        if text:
            yield text


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    question = (
        "What is the maximum medical "
        "assistance available?"
    )

    answer, sources = ask_question(
        question,
        scheme="TN_NHIS_2026"
    )

    print("\nANSWER:\n")

    print(answer)

    print("\nSOURCES:")

    for doc in sources:

        source = doc.metadata.get(
            "source",
            "Unknown"
        )

        page = doc.metadata.get(
            "page_label",
            "Unknown"
        )

        print(
            f"- {source} | Page {page}"
        )