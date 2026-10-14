import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000").replace(/\/$/, "");
const categories = ["Property Documents", "Rental Agreements", "Legal Documents"];

function fileType(name = "") {
  const ext = name.split(".").pop().toLowerCase();
  return ext === "pdf" ? "pdf" : ["doc", "docx"].includes(ext) ? "docx" : "txt";
}
function FileGlyph({ type }) {
  return <span className={`file-glyph ${type || "pdf"}`} aria-hidden="true">{type === "pdf" ? "↗" : type === "docx" ? "W" : "≡"}</span>;
}
function BotAvatar() { return <span className="avatar bot-avatar" aria-hidden="true">✣</span>; }
function UserAvatar() { return <span className="avatar user-avatar" aria-hidden="true">●</span>; }

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [activeCategory, setActiveCategory] = useState("All Documents");
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState("");
  const [pdfUrl, setPdfUrl] = useState("");
  const [page, setPage] = useState(1);
  const fileInput = useRef(null);
  const selectedDocument = documents.find(d => String(d.id) === String(selectedId)) || null;
  const visibleDocuments = activeCategory === "All Documents" ? documents : documents.filter(d => (d.category || "Property Documents") === activeCategory);

  async function loadDocuments() {
    try {
      const res = await fetch(`${API}/api/documents`);
      if (!res.ok) return;
      const data = await res.json();
      const list = Array.isArray(data) ? data : (data.documents || []);
      const normalized = list.map((d, i) => ({
        ...d,
        id: d.id ?? d.document_id ?? d.filename ?? d.name ?? String(i),
        name: d.name || d.filename || d.original_name || "Uploaded document",
        type: d.type || fileType(d.name || d.filename || ""),
        category: d.category || "Property Documents",
        time: d.time || "Available on backend",
      }));
      setDocuments(normalized);
      setSelectedId(current => current && normalized.some(d => String(d.id) === String(current)) ? current : String(normalized[0]?.id ?? ""));
    } catch {
      // The upload button still reports a useful message if the backend is not running.
    }
  }

  useEffect(() => { loadDocuments(); }, []);
  useEffect(() => {
    if (!selectedDocument) { setPdfUrl(""); return; }
    if (selectedDocument.preview_url) {
      setPdfUrl(selectedDocument.preview_url.startsWith("http") ? selectedDocument.preview_url : `${API}${selectedDocument.preview_url}`);
    } else if (selectedDocument.url) {
      setPdfUrl(selectedDocument.url.startsWith("http") ? selectedDocument.url : `${API}${selectedDocument.url}`);
    } else if (fileType(selectedDocument.name) === "pdf") {
      setPdfUrl(`${API}/api/documents/${encodeURIComponent(selectedDocument.name)}/file`);
    } else {
      setPdfUrl("");
    }
    setPage(1);
  }, [selectedId, documents]);

  async function uploadFiles(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    setUploading(true);
    setNotice("");
    try {
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        // Optional category is sent so the backend can keep the sidebar categories.
        form.append("category", activeCategory === "All Documents" ? "Property Documents" : activeCategory);
        const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || data.message || `Upload failed for ${file.name}`);
      }
      await loadDocuments();
      setNotice(`${files.length} file${files.length > 1 ? "s" : ""} uploaded. The backend should now index them for RAG.`);
    } catch (err) {
      setNotice(`Upload failed: ${err.message}. Check that Flask is running and POST /api/upload is implemented.`);
    } finally {
      setUploading(false);
    }
  }

  async function sendQuestion(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy) return;
    if (!selectedDocument) {
      setNotice("Upload and select a document before asking a question.");
      return;
    }
    setMessages(prev => [...prev, { role: "user", text }]);
    setQuestion("");
    setBusy(true);
    setNotice("");
    try {
      const res = await fetch(`${API}/api/qa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: text,
          document: selectedDocument.name,
          document_id: selectedDocument.id,
          source: selectedDocument.name,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || data.message || "Question request failed.");
      const answer = data.answer || data.response || data.result;
      if (!answer) throw new Error("The API response has no answer/response/result field.");
      setMessages(prev => [...prev, { role: "assistant", text: answer, sources: data.sources || data.source_documents || [] }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", text: `I couldn't get an answer from the backend. ${err.message} Check that POST /api/qa retrieves chunks for the selected document and returns JSON with an "answer" field.` }]);
    } finally {
      setBusy(false);
    }
  }

  async function removeDocument(doc, event) {
    event.stopPropagation();
    if (!window.confirm(`Remove ${doc.name} from the document list?`)) return;
    try {
      const res = await fetch(`${API}/api/documents/${encodeURIComponent(doc.name)}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Backend delete endpoint is not available.");
      }
      setMessages([]);
      await loadDocuments();
      setNotice("Document removed.");
    } catch (err) {
      setNotice(`Could not remove file: ${err.message}`);
    }
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand">
        <div className="brand-house" aria-hidden="true"><svg viewBox="0 0 48 48"><path d="M5 22 24 5l19 17" /><path d="M11 20v22h26V20M20 42V28h9v14" /><path d="M31 11V6h6v11" /></svg></div>
        <div><h1>Real Estate Document Intelligence</h1><p>Upload real estate documents and ask questions using AI (RAG)</p></div>
      </div>
      <nav className="category-nav">
        {categories.map((cat, i) => <button key={cat} className={`nav-chip ${["purple","green","yellow"][i]} ${activeCategory === cat ? "active" : ""}`} onClick={() => setActiveCategory(activeCategory === cat ? "All Documents" : cat)}><span>{["▤","⌂","⚖"][i]}</span>{cat}</button>)}
      </nav>
    </header>

    <main className="workspace">
      <aside className="panel sidebar">
        <button className="upload-button" onClick={() => fileInput.current?.click()} disabled={uploading}><span>＋</span>{uploading ? "Uploading and indexing..." : "Upload Document"}</button>
        <input ref={fileInput} type="file" accept=".pdf,.doc,.docx,.txt" multiple hidden onChange={uploadFiles} />
        <p className="supported">Supported formats: PDF, DOCX, TXT</p>
        <div className="section-heading"><h2>Uploaded Documents</h2><button className="refresh-button" onClick={loadDocuments} title="Refresh documents">↻</button></div>
        <div className="document-list">
          {visibleDocuments.map(doc => <div key={doc.id} className={`document-item ${String(selectedId) === String(doc.id) ? "selected" : ""}`} onClick={() => setSelectedId(String(doc.id))} role="button" tabIndex={0} onKeyDown={e => e.key === "Enter" && setSelectedId(String(doc.id))}>
            <FileGlyph type={doc.type || fileType(doc.name)} />
            <div className="document-meta"><span className="document-name">{doc.name}</span><span className="document-time">{doc.time}</span></div>
            <button className="delete-button" title={`Remove ${doc.name}`} aria-label={`Remove ${doc.name}`} onClick={e => removeDocument(doc, e)}>×</button>
          </div>)}
          {!visibleDocuments.length && <div className="empty-list">{documents.length ? "No documents in this category." : "No uploaded documents yet. Upload a file to get started."}</div>}
        </div>
        <div className="sidebar-foot"><span className="status-dot" /> {documents.length} documents from backend</div>
      </aside>

      <section className="panel chat-panel">
        <div className="panel-title chat-title"><span className="title-icon chat-icon">☏</span><h2>Chat with Your Documents</h2><span className="rag-pill">Live RAG</span></div>
        <div className="chat-messages">
          {!messages.length && <div className="welcome-card"><div className="welcome-icon">✦</div><h3>Ask your document anything</h3><p>Try questions about rent, property area, payment dates, responsibilities, clauses, or any detail in the selected file.</p></div>}
          {messages.map((m, i) => <div key={i} className={`message-row ${m.role === "user" ? "from-user" : "from-assistant"}`}>
            {m.role === "assistant" && <BotAvatar />}
            <div className={`message-bubble ${m.role}`}>{m.text.split("\n").map((line, j) => <span className="message-line" key={j}>{line || "\u00A0"}</span>)}
              {!!m.sources?.length && <small className="source-note">Sources: {m.sources.map(s => typeof s === "string" ? s : s.source || s.filename || s.name || "document").join(", ")}</small>}
            </div>
            {m.role === "user" && <UserAvatar />}
          </div>)}
          {busy && <div className="message-row from-assistant"><BotAvatar /><div className="message-bubble assistant typing">Searching selected document<span> •••</span></div></div>}
        </div>
        <form className="chat-composer" onSubmit={sendQuestion}>
          <input value={question} onChange={e => setQuestion(e.target.value)} placeholder={selectedDocument ? `Ask about ${selectedDocument.name}...` : "Upload a document to start asking questions..."} aria-label="Ask a question" />
          <button type="submit" disabled={busy || !question.trim() || !selectedDocument}><span>➤</span> Send</button>
        </form>
        <p className="chat-hint">Answers are requested from the selected document using your Flask + FAISS + Gemini RAG backend.</p>
      </section>

      <aside className="panel preview-panel">
        <div className="panel-title preview-title"><span className="title-icon document-title-icon">▤</span><h2>Document Preview</h2></div>
        <div className="preview-file">{selectedDocument ? <><FileGlyph type={selectedDocument.type || fileType(selectedDocument.name)} /><span>{selectedDocument.name}</span></> : <span>No document selected</span>}</div>
        {selectedDocument && fileType(selectedDocument.name) === "pdf" && pdfUrl ? <>
          <div className="pdf-toolbar"><span>PDF document</span><a href={pdfUrl} target="_blank" rel="noreferrer">Open ↗</a></div>
          <iframe key={pdfUrl} className="pdf-frame" src={pdfUrl} title={`Preview of ${selectedDocument.name}`} />
        </> : <div className="preview-placeholder">{selectedDocument ? <><FileGlyph type={selectedDocument.type || fileType(selectedDocument.name)} /><h3>{selectedDocument.name}</h3><p>This file type is not displayed in the built-in PDF preview. You can still ask questions about it after the backend has indexed it.</p></> : <><span className="empty-preview-icon">▤</span><h3>Your document preview will appear here</h3><p>Upload and select a PDF document to preview its actual pages.</p></>}</div>}
        <div className="preview-footer"><span className="status-dot" /> Actual PDF served by Flask backend</div>
      </aside>
    </main>
    {notice && <div className="toast" role="status"><span>{notice}</span><button onClick={() => setNotice("")} aria-label="Dismiss">×</button></div>}
  </div>;
}
