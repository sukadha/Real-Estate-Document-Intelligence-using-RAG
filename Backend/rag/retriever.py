from rag.vector_store import load_vector_store


def retrieve_documents(question, k=4):
    """
    Retrieve the top k relevant document chunks
    from the FAISS vector database.
    """

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    vector_store = load_vector_store()

    documents = vector_store.similarity_search(
        question,
        k=k
    )

    print(f"\nQuestion: {question}")
    print(f"Relevant chunks retrieved: {len(documents)}")

    return documents


if __name__ == "__main__":

    while True:
        question = input(
            "\nEnter your question (type 'exit' to stop): "
        ).strip()

        if question.lower() == "exit":
            print("Exiting the retriever. Goodbye!")
            break

        if not question:
            print("Please enter a valid question.")
            continue

        try:
            results = retrieve_documents(question, k=4)

            for i, document in enumerate(results, start=1):
                print(f"\n--- Result {i} ---")
                print("Text:", document.page_content)
                print("Property:", document.metadata.get("property"))
                print("Document:", document.metadata.get("document_type"))
                print("Page:", document.metadata.get("page"))
                print("Source:", document.metadata.get("source"))

        except Exception as error:
            print(f"Error retrieving documents: {error}")