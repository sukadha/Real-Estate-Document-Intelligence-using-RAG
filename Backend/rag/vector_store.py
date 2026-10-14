import os

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from rag.embeddings import get_embedding_model


FAISS_PATH = "vector_db/faiss_index"


def create_vector_store(chunks):
    """
    Create a FAISS vector database from text chunks
    and save it locally.
    """

    if not chunks:
        raise ValueError("No text chunks available to store.")

    embedding_model = get_embedding_model()

    documents = []

    for chunk in chunks:
        metadata = {
            "page": chunk["page"],
            "property": chunk["property"],
            "document_type": chunk["document_type"],
            "source": chunk["source"],
            "file_path": chunk["file_path"]
        }

        document = Document(
            page_content=chunk["text"],
            metadata=metadata
        )

        documents.append(document)

    # Create the FAISS vector database
    vector_store = FAISS.from_documents(
        documents,
        embedding_model
    )

    # Create the directory if it does not exist
    os.makedirs(FAISS_PATH, exist_ok=True)

    # Save the FAISS index locally
    vector_store.save_local(FAISS_PATH)

    print(f"Total chunks stored: {len(documents)}")
    print(f"FAISS index saved at: {FAISS_PATH}")

    return vector_store


def load_vector_store():
    """
    Load an existing FAISS index from disk.
    """

    if not os.path.exists(
        os.path.join(FAISS_PATH, "index.faiss")
    ):
        raise FileNotFoundError(
            "FAISS index not found. Create the vector store first."
        )

    embedding_model = get_embedding_model()

    vector_store = FAISS.load_local(
        FAISS_PATH,
        embedding_model,
        allow_dangerous_deserialization=True
    )

    print("FAISS vector database loaded successfully.")

    return vector_store