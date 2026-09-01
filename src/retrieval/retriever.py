from functools import lru_cache

from src.vectorstore.runtime_store import get_vector_store


@lru_cache(maxsize=2)
def get_retriever(scheme=None):

    vector_store = get_vector_store()

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