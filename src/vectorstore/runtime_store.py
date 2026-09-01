import os
from pathlib import Path
from functools import lru_cache

from langchain_chroma import Chroma

from src.ingestion.pdf_loader import load_pdfs
from src.ingestion.text_splitter import split_documents
from src.embeddings.embedding_model import get_embedding_model


BASE_DIR = Path(__file__).resolve().parents[2]

LOCAL_CHROMA_DIR = BASE_DIR / "chroma_db"

CLOUD_CHROMA_DIR = Path("/tmp/policywise_chroma_db")


@lru_cache(maxsize=1)
def get_vector_store():

    use_cloud_store = (
        os.getenv("USE_CLOUD_CHROMA", "false").lower()
        == "true"
    )

    embeddings = get_embedding_model()

    # ---------------------------------
    # STREAMLIT CLOUD
    # ---------------------------------
    if use_cloud_store:

        print("Using Streamlit Cloud runtime ChromaDB")

        if not CLOUD_CHROMA_DIR.exists():

            print("Building ChromaDB from PDFs...")

            documents = load_pdfs()

            chunks = split_documents(
                documents
            )

            vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=str(
                    CLOUD_CHROMA_DIR
                )
            )

            print(
                "Cloud ChromaDB created successfully"
            )

            return vector_store

        return Chroma(
            persist_directory=str(
                CLOUD_CHROMA_DIR
            ),
            embedding_function=embeddings
        )

    # ---------------------------------
    # LOCAL DEVELOPMENT
    # ---------------------------------

    print("Using local ChromaDB")

    return Chroma(
        persist_directory=str(
            LOCAL_CHROMA_DIR
        ),
        embedding_function=embeddings
    )