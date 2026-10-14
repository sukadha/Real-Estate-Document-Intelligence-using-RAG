from langchain_community.embeddings import HuggingFaceEmbeddings


def get_embedding_model():
    """
    Load a local embedding model.
    """

    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    return embedding_model


def generate_embeddings(chunks):
    """
    Convert text chunks into numerical vectors.
    """

    embedding_model = get_embedding_model()

    texts = [chunk["text"] for chunk in chunks]

    embeddings = embedding_model.embed_documents(texts)

    print(f"Total chunks embedded: {len(embeddings)}")

    if embeddings:
        print(f"Vector dimensions: {len(embeddings[0])}")
        print(f"First vector sample: {embeddings[0][:5]}")

    return embeddings