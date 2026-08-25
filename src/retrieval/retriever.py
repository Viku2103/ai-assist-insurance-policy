from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma

from src.embeddings.embedding_model import get_embedding_model


BASE_DIR = Path(__file__).resolve().parents[2]
CHROMA_DIR = BASE_DIR / "chroma_db"


@lru_cache(maxsize=2)
def get_retriever(scheme=None):

    embeddings = get_embedding_model()

    vector_store = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings
    )

    if scheme:

        retriever = vector_store.as_retriever(
            search_kwargs={
                "k": 3,
                "filter": {
                    "scheme": scheme
                }
            }
        )

    else:

        retriever = vector_store.as_retriever(
            search_kwargs={
                "k": 3
            }
        )

    return retriever


if __name__ == "__main__":

    retriever = get_retriever(
        scheme="TN_NHIS_2026"
    )

    question = (
        "What is the maximum medical assistance available?"
    )

    results = retriever.invoke(
        question
    )

    for i, doc in enumerate(
        results,
        start=1
    ):

        print(
            f"\n--- Result {i} ---"
        )

        print(
            doc.page_content
        )

        print(
            "\nSource:",
            doc.metadata.get("source")
        )

        print(
            "Page:",
            doc.metadata.get("page_label")
        )