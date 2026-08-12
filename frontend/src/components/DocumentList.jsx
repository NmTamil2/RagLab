import DocumentExtract from "./DocumentExtract";
import { formatFileSize } from "../utils/formatFileSize";
import "./DocumentList.css";

/**
 * Shows the documents uploaded during this session.
 *
 * @param {{ documents: Array<object> }} props
 *
 * This component holds no state of its own — it only renders what it is given.
 * That makes it easy to reason about and reuse.
 */
function DocumentList({ documents }) {
  if (documents.length === 0) {
    return (
      <section className="card">
        <h2 className="card-title">Uploaded Documents</h2>
        <p className="card-subtitle">
          No documents yet. Upload a PDF to see it listed here.
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2 className="card-title">
        Uploaded Documents <span className="count-badge">{documents.length}</span>
      </h2>

      <ul className="document-list">
        {/* key must be stable and unique — the server-generated ID is ideal. */}
        {documents.map((document) => (
          <li key={document.document_id} className="document-item">
            <div className="document-name">
              <span className="document-badge">{document.file_type}</span>
              {document.filename}
            </div>
            <dl className="document-meta">
              <dt>Size</dt>
              <dd>{formatFileSize(document.file_size)}</dd>
              <dt>ID</dt>
              <dd className="document-id">{document.document_id}</dd>
            </dl>

            <DocumentExtract documentId={document.document_id} />
          </li>
        ))}
      </ul>
    </section>
  );
}

export default DocumentList;
