from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.ingestion.pdf_loader import load_pdfs


def split_documents(documents):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = text_splitter.split_documents(documents)

    print(f"Total chunks created: {len(chunks)}")

    return chunks


if __name__ == "__main__":

    documents = load_pdfs()

    chunks = split_documents(documents)

    if chunks:
        print("\nFirst chunk:")
        print(chunks[0].page_content)

        print("\nFirst chunk metadata:")
        print(chunks[0].metadata)