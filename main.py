from src.generation.rag_chain import ask_question


def main():

    print("=" * 50)
    print("              POLICYWISE AI")
    print(" Insurance Policy Question Answering System")
    print("=" * 50)

    print("\nChoose Knowledge Base:")
    print("1. Synthetic Insurance")
    print("2. Tamil Nadu NHIS 2026")

    choice = input("\nEnter choice (1 or 2): ")

    if choice == "1":
        selected_scheme = "generic_insurance"
        print("\nSelected: Synthetic Insurance")

    elif choice == "2":
        selected_scheme = "TN_NHIS_2026"
        print("\nSelected: Tamil Nadu NHIS 2026")

    else:
        print("\nInvalid choice.")
        return

    while True:

        question = input(
            "\nAsk a question about your insurance policies\n"
            "(type 'exit' to quit): "
        )

        if question.lower() == "exit":
            print("\nThank you for using PolicyWise AI.")
            break

        if not question.strip():
            print("Please enter a question.")
            continue

        try:

            answer, sources = ask_question(
                question,
                scheme=selected_scheme
            )

            print("\nANSWER:")
            print(answer)

            print("\nSOURCES:")

            displayed_sources = set()

            for doc in sources:

                source = doc.metadata.get(
                    "source",
                    "Unknown"
                )

                page = doc.metadata.get(
                    "page_label",
                    "Unknown"
                )

                scheme = doc.metadata.get(
                    "scheme",
                    "Unknown"
                )

                source_info = (
                    source,
                    page,
                    scheme
                )

                if source_info not in displayed_sources:

                    print(
                        f"- {source} | Page {page}"
                    )

                    displayed_sources.add(
                        source_info
                    )

        except Exception as error:

            print(
                f"\nUnable to process question: {error}"
            )


if __name__ == "__main__":
    main()