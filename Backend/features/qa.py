import os

import google.generativeai as genai
from dotenv import load_dotenv

from rag.retriever import retrieve_documents


# Load environment variables from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Please check your .env file."
    )


# Configure Gemini API
genai.configure(api_key=api_key)

# Gemini 2.5 Flash
model = genai.GenerativeModel("gemini-2.5-flash")


def answer_question(question):
    """
    Retrieve relevant chunks from FAISS
    and generate an answer using Gemini 2.5 Flash.
    """

    if not question or not question.strip():
        return "Please enter a valid question."

    # Identify the requested property, if specified
    question_lower = question.lower()

    requested_property = None

    if "property a" in question_lower:
        requested_property = "property_A"
    elif "property b" in question_lower:
        requested_property = "property_B"

    # Retrieve relevant chunks from FAISS
    documents = retrieve_documents(question, k=8)

    # Debug: Display the retrieved chunks
    print("\n========== RETRIEVED CONTEXT ==========")

    for i, document in enumerate(documents, start=1):
        print(f"\n--- Chunk {i} ---")
        print("Property:", document.metadata.get("property"))
        print("Document:", document.metadata.get("document_type"))
        print("Page:", document.metadata.get("page"))
        print("Text:", document.page_content)

    print("\n=======================================")

    # Filter results to the requested property
    if requested_property:
        property_documents = [
            document
            for document in documents
            if document.metadata.get("property") == requested_property
        ]

        # If the first search did not return that property,
        # search again with the property name included.
        if not property_documents:
            documents = retrieve_documents(
                f"{requested_property.replace('_', ' ')} {question}",
                k=12
            )

            property_documents = [
                document
                for document in documents
                if document.metadata.get("property") == requested_property
            ]

        documents = property_documents

    if not documents:
        return (
            "No relevant information was retrieved for this question. "
            "Check the PDF content and FAISS index."
        )

    # Combine retrieved text into one context
    context = "\n\n".join(
        (
            f"Property: {document.metadata.get('property')}\n"
            f"Document: {document.metadata.get('document_type')}\n"
            f"Page: {document.metadata.get('page')}\n"
            f"Content: {document.page_content}"
        )
        for document in documents
    )

    # Prompt for Gemini
    prompt = f"""
You are a Real Estate Document Intelligence assistant.

Answer the question using the supplied document context.

Rules:
1. Use only facts explicitly supported by the context.
2. Read all relevant chunks before answering.
3. If a security deposit, rent, or other amount is present,
   report the exact amount as written.
4. Do not confuse Property A with Property B.
5. Do not invent information or amounts.
6. If the context does not contain the answer, clearly say so.
7. Give a short, direct answer.
8. Mention the source document and page when available.

Requested property: {requested_property or "Not specified"}

Document context:
{context}

User question:
{question}

Answer:
"""

    # Generate the answer
    try:
        response = model.generate_content(prompt)

        if response.text:
            return response.text

        return "Gemini returned an empty response. Please try again."

    except Exception as error:
        return f"Gemini API error: {error}"


if __name__ == "__main__":

    print("=" * 50)
    print("Real Estate Document Intelligence")
    print("FAISS + Gemini 2.5 Flash")
    print("=" * 50)

    while True:
        question = input(
            "\nAsk a property question (or type 'exit'): "
        ).strip()

        if question.lower() == "exit":
            print("Goodbye!")
            break

        if not question:
            print("Please enter a question.")
            continue

        try:
            answer = answer_question(question)

            print("\n========== FINAL ANSWER ==========")
            print(answer)
            print("==================================")

        except Exception as error:
            print(f"Error: {error}")