
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from rag.document_loader import load_all_documents
from rag.text_splitter import split_text
from rag.vector_store import create_vector_store, load_vector_store
from features.qa import answer_question


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
UPLOAD_DIR = os.path.join(DOCUMENTS_DIR, "property_A")
FAISS_DIR = os.path.join(BASE_DIR, "vector_db", "faiss_index")

os.makedirs(UPLOAD_DIR, exist_ok=True)

load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

ALLOWED_EXTENSIONS = {"pdf"}


# --------------------------------------------------
# 2. HELPER FUNCTIONS
# --------------------------------------------------

def json_error(message, status_code=400):
    return jsonify({
        "status": "error",
        "message": message
    }), status_code


def get_pdf_path(filename):
    """Find a PDF by its relative path or filename."""
    safe_name = os.path.normpath(filename)

    if os.path.isabs(safe_name) or safe_name.startswith(".."):
        return None

    candidate = os.path.abspath(
        os.path.join(DOCUMENTS_DIR, safe_name)
    )

    if os.path.commonpath([DOCUMENTS_DIR, candidate]) != DOCUMENTS_DIR:
        return None

    if os.path.isfile(candidate) and candidate.lower().endswith(".pdf"):
        return candidate

    # If only the filename was supplied, search document subfolders.
    matches = []

    for root, _, files in os.walk(DOCUMENTS_DIR):
        if os.path.basename(safe_name) in files:
            matches.append(
                os.path.join(root, os.path.basename(safe_name))
            )

    if len(matches) == 1:
        return matches[0]

    return None


def rebuild_faiss_index():
    """Rebuild the FAISS index from PDFs currently in documents/."""
    documents = load_all_documents()

    if not documents:
        raise ValueError(
            "No readable PDF documents were found in the documents folder."
        )

    chunks = split_text(documents)

    if not chunks:
        raise ValueError(
            "No text chunks were created. Check whether the PDFs contain extractable text."
        )

    create_vector_store(chunks)

    unique_files = {
        doc.get("file_path") or doc.get("source")
        for doc in documents
        if doc.get("file_path") or doc.get("source")
    }

    return len(unique_files), len(chunks)


# --------------------------------------------------
# 3. HOME API
# GET /
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "success",
        "message": "Welcome to Real Estate Document Intelligence API",
        "vector_database": "FAISS",
        "llm": "Gemini 2.5 Flash",
        "endpoints": {
            "health": "GET /api/health",
            "upload": "POST /api/upload",
            "documents": "GET /api/documents",
            "index": "POST /api/index",
            "ask": "POST /api/ask or POST /api/qa",
            "pdf_preview": "GET /api/files/<path:filename>"
        }
    }), 200


# --------------------------------------------------
# 4. HEALTH CHECK
# GET /api/health
# --------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "success",
        "message": "Real Estate RAG Backend is running"
    }), 200


# --------------------------------------------------
# 5. UPLOAD PDF
# POST /api/upload
# multipart/form-data: file=<PDF>
# --------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def upload_document():
    saved_path = None

    try:
        if "file" not in request.files:
            return json_error("No file was provided in the upload request.")

        uploaded_file = request.files["file"]

        if not uploaded_file.filename:
            return json_error("Please select a file.")

        filename = secure_filename(uploaded_file.filename)

        if not filename or "." not in filename:
            return json_error("Invalid filename.")

        extension = filename.rsplit(".", 1)[1].lower()

        if extension not in ALLOWED_EXTENSIONS:
            return json_error(
                "Only PDF files are currently supported by this backend."
            )

        # Optional property folder, defaulting to property_A.
        property_name = secure_filename(
            request.form.get("property", "property_A")
        )

        if not property_name:
            property_name = "property_A"

        target_dir = os.path.join(DOCUMENTS_DIR, property_name)
        os.makedirs(target_dir, exist_ok=True)

        saved_path = os.path.join(target_dir, filename)
        uploaded_file.save(saved_path)

        # Rebuild index to include the newly uploaded PDF.
        document_count, chunk_count = rebuild_faiss_index()

        relative_path = os.path.relpath(
            saved_path, DOCUMENTS_DIR
        ).replace("\\", "/")

        return jsonify({
            "status": "success",
            "message": "PDF uploaded and indexed successfully.",
            "filename": filename,
            "id": relative_path,
            "type": "pdf",
            "category": request.form.get(
                "category", "Property Documents"
            ),
            "documents": document_count,
            "chunks": chunk_count,
            "preview_url": "/api/files/" + relative_path
        }), 200

    except Exception as error:
        app.logger.exception("Document upload failed")

        # Remove the just-uploaded file if indexing failed.
        # Existing files are not deleted on an overwrite failure.
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500


# --------------------------------------------------
# 6. LIST UPLOADED DOCUMENTS
# GET /api/documents
# --------------------------------------------------

@app.route("/api/documents", methods=["GET"])
def list_documents():
    try:
        results = []

        for root, _, filenames in os.walk(DOCUMENTS_DIR):
            for filename in sorted(filenames):
                if not filename.lower().endswith(".pdf"):
                    continue

                full_path = os.path.join(root, filename)

                relative_path = os.path.relpath(
                    full_path, DOCUMENTS_DIR
                ).replace("\\", "/")

                property_name = relative_path.split("/")[0]

                results.append({
                    "id": relative_path,
                    "name": filename,
                    "type": "pdf",
                    "category": "Rental Agreements"
                    if "agreement" in filename.lower()
                    else "Property Documents",
                    "property": property_name,
                    "preview_url": "/api/files/" + relative_path
                })

        return jsonify({
            "status": "success",
            "documents": results
        }), 200

    except Exception as error:
        app.logger.exception("Listing documents failed")
        return json_error(str(error), 500)


# --------------------------------------------------
# 7. SERVE PDF FOR FRONTEND PREVIEW
# GET /api/files/<path:filename>
# --------------------------------------------------

@app.route("/api/files/<path:filename>", methods=["GET"])
def serve_pdf(filename):
    try:
        path = get_pdf_path(filename)

        if not path:
            return json_error("PDF document not found.", 404)

        directory = os.path.dirname(path)
        actual_filename = os.path.basename(path)

        return send_from_directory(directory, actual_filename)

    except Exception as error:
        app.logger.exception("PDF preview failed")
        return json_error(str(error), 500)


# --------------------------------------------------
# 8. INDEX DOCUMENTS
# POST /api/index
# --------------------------------------------------

@app.route("/api/index", methods=["POST"])
def index_documents():
    try:
        document_count, chunk_count = rebuild_faiss_index()

        return jsonify({
            "status": "success",
            "message": "Documents indexed successfully",
            "documents": document_count,
            "chunks": chunk_count
        }), 200

    except Exception as error:
        app.logger.exception("Document indexing failed")
        return json_error(str(error), 500)


# --------------------------------------------------
# 9. ASK A QUESTION
# POST /api/ask or POST /api/qa
#
# JSON:
# {
#   "question": "What is the security deposit?",
#   "document": "rental_agreement.pdf"
# }
# --------------------------------------------------

@app.route("/api/ask", methods=["GET", "POST"])
@app.route("/api/qa", methods=["POST"])
def ask():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            question = data.get("question", "")
        else:
            data = {}
            question = request.args.get("question", "")

        if not isinstance(question, str) or not question.strip():
            return json_error("Please provide a valid question.")

        question = question.strip()

        # Check that the vector index exists.
        if not os.path.isfile(os.path.join(FAISS_DIR, "index.faiss")):
            return json_error(
                "FAISS index not found. Upload a PDF or call POST /api/index first.",
                400
            )

        # Keep the selected document available to the QA layer.
        # NOTE: answer_question(question) alone does not filter by filename.
        # Filename filtering must also be implemented in features/qa.py
        # and the retriever to guarantee document-specific answers.
        answer = answer_question(question)

        if not answer:
            answer = (
                "I couldn't find a reliable answer in the indexed documents."
            )

        return jsonify({
            "status": "success",
            "question": question,
            "answer": answer
        }), 200

    except Exception as error:
        app.logger.exception("Question answering failed")
        return json_error(str(error), 500)


# --------------------------------------------------
# 10. HANDLE COMMON ERRORS
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(_error):
    return json_error("File exceeds the 20 MB upload limit.", 413)


@app.errorhandler(404)
def not_found(_error):
    return json_error("API endpoint not found.", 404)


# --------------------------------------------------
# 11. START SERVER
# --------------------------------------------------

if __name__ == "__main__":
    print("=" * 55)
    print("REAL ESTATE DOCUMENT INTELLIGENCE")
    print("Backend: Flask")
    print("Vector Database: FAISS")
    print("LLM: Gemini 2.5 Flash")
    print("Server: http://127.0.0.1:5000")
    print("=" * 55)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
