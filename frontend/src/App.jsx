import { useState } from "react";
import HealthStatus from "./components/HealthStatus";
import DocumentUpload from "./components/DocumentUpload";
import DocumentList from "./components/DocumentList";
import "./App.css";

/**
 * Root component: the page shell.
 *
 * App owns the list of uploaded documents because two children need it —
 * DocumentUpload adds to it, DocumentList displays it. Holding shared state in
 * the closest common parent is the standard React pattern ("lifting state up").
 *
 * Note: this list lives in memory only, so it resets on page refresh. Files
 * themselves stay on the backend disk. A persistent list needs a database,
 * which belongs to a later milestone.
 */
function App() {
  const [documents, setDocuments] = useState([]);

  function handleUploadSuccess(newDocument) {
    // Build a new array instead of pushing into the old one — React only
    // re-renders when it sees a new array reference.
    setDocuments((currentDocuments) => [newDocument, ...currentDocuments]);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">RAGLab</h1>
        <p className="app-tagline">
          An educational, production-style Retrieval-Augmented Generation
          application — built milestone by milestone to learn RAG, embeddings,
          vector search, reranking and evaluation from the ground up.
        </p>
      </header>

      <main>
        <HealthStatus />
        <DocumentUpload onUploadSuccess={handleUploadSuccess} />
        <DocumentList documents={documents} />
      </main>

      <footer className="app-footer">
        Step 3 — PDF parsing and text extraction
      </footer>
    </div>
  );
}

export default App;
