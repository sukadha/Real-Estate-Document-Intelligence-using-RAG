from features.qa import model
from rag.retriever import retrieve_documents
from rag.prompts import SUMMARY_PROMPT


def summarize_document(question):
    """Summarize relevant real-estate document content."""

    if not question or not question.strip():
        return "Please enter a valid question."

    documents = retrieve_documents(question, k=8)

    if not documents:
        return "Information not found in the uploaded documents."

    context = "\n\n".join(
        f"Property: {doc.metadata.get('property')}\n"
        f"Document: {doc.metadata.get('document_type')}\n"
        f"Page: {doc.metadata.get('page')}\n"
        f"Content: {doc.page_content}"
        for doc in documents
    )

    prompt = SUMMARY_PROMPT.format(context=context)

    try:
        response = model.generate_content(prompt)

        if response.text:
            return response.text

        return "Gemini returned an empty response."

    except Exception as error:
        return f"Summarization error: {error}"


if __name__ == "__main__":
    print("\n=== Real Estate Document Summarization ===")
    print("Type 'exit' to stop.")

    while True:
        question = input(
            "\nEnter your question or document to summarize: "
        ).strip()

        if question.lower() == "exit":
            print("Program stopped.")
            break

        if not question:
            print("Please enter a question.")
            continue

        print("\nGenerating summary...")

        result = summarize_document(question)

        print("\n--- Summary / Answer ---")
        print(result)