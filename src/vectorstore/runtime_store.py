import os
from pathlib import Path
from functools import lru_cache

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from langchain_chroma import Chroma

from src.ingestion.pdf_loader import load_pdfs
from src.ingestion.text_splitter import split_documents
from src.embeddings.embedding_model import get_embedding_model


# Project root
BASE_DIR = Path(__file__).resolve().parents[2]

# Existing local ChromaDB
LOCAL_CHROMA_DIR = BASE_DIR / "chroma_db"

# Temporary ChromaDB used by Streamlit Cloud
CLOUD_CHROMA_DIR = Path("/tmp/policywise_chroma_db")


@lru_cache(maxsize=1)
def get_vector_store():

    # ---------------------------------
    # Check whether we are on cloud
    # ---------------------------------

    try:
        cloud_setting = st.secrets["USE_CLOUD_CHROMA"]

    except (StreamlitSecretNotFoundError, KeyError):
        cloud_setting = os.getenv(
            "USE_CLOUD_CHROMA",
            "false"
        )

    use_cloud_store = (
        str(cloud_setting).lower() == "true"
    )

    # Get the same embedding model
    embeddings = get_embedding_model()


    # ---------------------------------
    # STREAMLIT CLOUD
    # ---------------------------------

    if use_cloud_store:

        print("Using Streamlit Cloud runtime ChromaDB")

        # If cloud database does not exist,
        # create it from the PDFs
        if not CLOUD_CHROMA_DIR.exists():

            print("Building ChromaDB from PDFs...")

            # Load all PDFs
            documents = load_pdfs()

            # Split documents into chunks
            chunks = split_documents(
                documents
            )

            # Create fresh ChromaDB
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

        # If already created, connect to it
        print("Using existing cloud runtime ChromaDB")

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