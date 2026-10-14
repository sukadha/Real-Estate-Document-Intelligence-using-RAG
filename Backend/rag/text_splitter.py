def split_text(documents, chunk_size=500, chunk_overlap=100):
    """
    Split extracted PDF text into smaller chunks.
    Preserve the original document metadata.
    """

    split_documents = []

    for document in documents:
        text = document["text"]
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Prefer splitting at a space when possible
            if end < len(text):
                space_position = text.rfind(" ", start, end)

                if space_position > start:
                    end = space_position

            chunk = text[start:end].strip()

            if chunk:
                split_documents.append({
                    **document,
                    "text": chunk
                })

            if end >= len(text):
                break

            start = max(end - chunk_overlap, start + 1)

    print(f"Total original pages: {len(documents)}")
    print(f"Total text chunks: {len(split_documents)}")

    return split_documents