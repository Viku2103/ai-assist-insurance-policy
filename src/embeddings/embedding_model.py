from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings


@lru_cache(maxsize=1)
def get_embedding_model():

    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


if __name__ == "__main__":

    embeddings = get_embedding_model()

    test_vector = embeddings.embed_query(
        "What documents are required for an insurance claim?"
    )

    print("Embedding created successfully")
    print("Vector length:", len(test_vector))