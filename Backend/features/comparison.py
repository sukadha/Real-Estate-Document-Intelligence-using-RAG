from features.qa import model
from rag.retriever import retrieve_documents
from rag.prompts import COMPARISON_PROMPT


def compare_properties(question):
    """
    Compare Property A and Property B using FAISS and Gemini.
    """

    if not question or not question.strip():
        return "Please enter a valid comparison question."

    # Retrieve relevant chunks for the comparison question
    property_a_docs = retrieve_documents(
        f"Property A {question}",
        k=12
    )

    property_b_docs = retrieve_documents(
        f"Property B {question}",
        k=12
    )

    # Keep only the chunks belonging to the correct property
    property_a_docs = [
        doc for doc in property_a_docs
        if doc.metadata.get("property") == "property_A"
    ]

    property_b_docs = [
        doc for doc in property_b_docs
        if doc.metadata.get("property") == "property_B"
    ]

    if not property_a_docs or not property_b_docs:
        return (
            "Could not retrieve enough information for both properties. "
            "Try another question or check the uploaded documents."
        )

    # Build context with source metadata
    context_parts = []

    for property_name, documents in [
        ("Property A", property_a_docs),
        ("Property B", property_b_docs)
    ]:
        for doc in documents:
            context_parts.append(
                f"Property: {property_name}\n"
                f"Document: {doc.metadata.get('document_type')}\n"
                f"Page: {doc.metadata.get('page')}\n"
                f"Content: {doc.page_content}"
            )

    context = "\n\n".join(context_parts)

    # Add the user's question to the comparison prompt
    prompt = (
        COMPARISON_PROMPT
        + f"\n\nUser's comparison question:\n{question}\n\nAnswer:"
    )

    # Include the retrieved context in the prompt
    prompt = prompt.replace(
        "{context}",
        context
    )

    try:
        response = model.generate_content(prompt)

        if response.text:
            return response.text

        return "Gemini returned an empty response."

    except Exception as error:
        return f"Property comparison error: {error}"


if __name__ == "__main__":

    print("=" * 50)
    print("Real Estate Property Comparison")
    print("Powered by FAISS and Gemini 2.5 Flash")
    print("Type 'exit' to stop.")
    print("=" * 50)

    while True:
        question = input(
            "\nWhat would you like to compare between Property A and B? "
        ).strip()

        if question.lower() == "exit":
            print("Program stopped.")
            break

        if not question:
            print("Please enter a comparison question.")
            continue

        print("\nComparing properties...")

        result = compare_properties(question)

        print("\n========== COMPARISON RESULT ==========")
        print(result)
        print("=======================================")