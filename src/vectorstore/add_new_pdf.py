from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma

from src.ingestion.text_splitter import split_documents
from src.embeddings.embedding_model import get_embedding_model


BASE_DIR = Path(__file__).resolve().parents[2]

NEW_PDF = BASE_DIR / "docs" / "government" / "TN_Ins.pdf"

CHROMA_DIR = BASE_DIR / "chroma_db"


def add_new_pdf():

    print("Loading new PDF:", NEW_PDF)

    loader = PyPDFLoader(str(NEW_PDF))

    pages = loader.load()

    print("Pages loaded:", len(pages))

    # Add the same government scheme metadata
    for page in pages:
        page.metadata["category"] = "government"
        page.metadata["scheme"] = "TN_NHIS_2026"

    # Split pages into chunks
    chunks = split_documents(pages)

    print("Chunks created:", len(chunks))

    # Use the same embedding model as existing database
    embeddings = get_embedding_model()

    # Connect to existing ChromaDB
    vector_store = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings
    )

    # Add ONLY this new PDF
    vector_store.add_documents(chunks)

    print("TN_Ins.pdf added successfully!")


if __name__ == "__main__":
    add_new_pdf()