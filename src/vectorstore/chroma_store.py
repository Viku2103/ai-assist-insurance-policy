from pathlib import Path

from langchain_chroma import Chroma

from src.ingestion.pdf_loader import load_pdfs
from src.ingestion.text_splitter import split_documents
from src.embeddings.embedding_model import get_embedding_model


BASE_DIR = Path(__file__).resolve().parents[2]
CHROMA_DIR = BASE_DIR / "chroma_db"


def create_vector_store():

    documents = load_pdfs()

    chunks = split_documents(
        documents
    )

    embeddings = get_embedding_model()

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR)
    )

    print(
        "\nVector store created successfully"
    )

    return vector_store


if __name__ == "__main__":

    create_vector_store()