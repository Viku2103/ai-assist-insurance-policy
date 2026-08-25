from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader


# Project root
BASE_DIR = Path(__file__).resolve().parents[2]

# Document folders inside the project
SYNTHETIC_FOLDER = BASE_DIR / "docs" / "synthetic"
GOVERNMENT_FOLDER = BASE_DIR / "docs" / "government"


def load_pdfs():

    documents = []

    # -----------------------------
    # Load Synthetic PDFs
    # -----------------------------

    synthetic_files = list(
        SYNTHETIC_FOLDER.glob("*.pdf")
    )

    print(
        f"Synthetic PDFs found: {len(synthetic_files)}"
    )

    for pdf_file in synthetic_files:

        print(
            f"Loading: {pdf_file}"
        )

        loader = PyPDFLoader(
            str(pdf_file)
        )

        pages = loader.load()

        for page in pages:

            page.metadata["category"] = "synthetic"
            page.metadata["scheme"] = "generic_insurance"

        documents.extend(
            pages
        )


    # -----------------------------
    # Load Government PDFs
    # -----------------------------

    government_files = list(
        GOVERNMENT_FOLDER.glob("*.pdf")
    )

    print(
        f"\nGovernment PDFs found: {len(government_files)}"
    )

    for pdf_file in government_files:

        print(
            f"Loading: {pdf_file}"
        )

        loader = PyPDFLoader(
            str(pdf_file)
        )

        pages = loader.load()

        for page in pages:

            page.metadata["category"] = "government"
            page.metadata["scheme"] = "TN_NHIS_2026"

        documents.extend(
            pages
        )


    print(
        f"\nTotal pages loaded: {len(documents)}"
    )

    return documents


if __name__ == "__main__":

    documents = load_pdfs()

    if documents:

        print(
            "\nFirst page content:\n"
        )

        print(
            documents[0].page_content[:1000]
        )

        print(
            "\nMetadata:\n"
        )

        print(
            documents[0].metadata
        )