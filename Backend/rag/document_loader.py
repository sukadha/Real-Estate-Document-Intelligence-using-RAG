
import os
from pypdf import PdfReader
from utils.preprocessing import clean_text


def load_pdf(file_path):
    """
    Extract text from each page of a PDF file.

    Returns a list of dictionaries containing
    the extracted text and page number.
    """
    pages = []

    try:
        reader = PdfReader(file_path)

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            if text:
                text = clean_text(text)

                if text:
                    pages.append({
                        "text": text,
                        "page": page_number
                    })

    except Exception as error:
        print(f"Error loading PDF {file_path}: {error}")

    return pages


def load_all_documents(documents_folder="documents"):
    """
    Load all PDF documents from each property folder.

    Expected structure:
        documents/
            property_A/
            property_B/
    """
    all_documents = []

    if not os.path.exists(documents_folder):
        print(f"Documents folder not found: {documents_folder}")
        return all_documents

    for property_name in sorted(os.listdir(documents_folder)):
        property_path = os.path.join(
            documents_folder,
            property_name
        )

        if not os.path.isdir(property_path):
            continue

        for filename in sorted(os.listdir(property_path)):
            if not filename.lower().endswith(".pdf"):
                continue

            file_path = os.path.join(
                property_path,
                filename
            )

            print(f"Loading: {property_name}/{filename}")

            pages = load_pdf(file_path)

            for page_data in pages:
                all_documents.append({
                    "text": page_data["text"],
                    "page": page_data["page"],
                    "property": property_name,
                    "document_type": os.path.splitext(filename)[0],
                    "source": filename,
                    "file_path": file_path
                })

    print(f"\nTotal pages loaded: {len(all_documents)}")

    return all_documents
