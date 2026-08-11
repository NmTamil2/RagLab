import { useRef, useState } from "react";
import { uploadDocument } from "../api/client";
import { formatFileSize } from "../utils/formatFileSize";
import "./DocumentUpload.css";

/**
 * Lets the user pick a PDF and send it to the backend.
 *
 * @param {{ onUploadSuccess: (document: object) => void }} props
 *   onUploadSuccess is called with the metadata returned by the API, so the
 *   parent can add the document to its list. Passing a callback upward like
 *   this keeps the list of documents owned by one component (App).
 */
function DocumentUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // A ref gives us a handle on the real <input> element so we can clear it
  // after a successful upload. React state alone cannot reset a file input.
  const fileInputRef = useRef(null);

  function handleFileChange(event) {
    const file = event.target.files[0] ?? null;

    setSelectedFile(file);
    // Any new selection clears the results of the previous attempt.
    setError(null);
    setSuccessMessage(null);
  }

  async function handleUpload() {
    // Guard 1: nothing chosen.
    if (!selectedFile) {
      setError("Please choose a PDF file first.");
      return;
    }

    // Guard 2: obviously wrong type. The backend checks this properly too —
    // this check just gives instant feedback without a round trip.
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }

    // Guard 3: empty file.
    if (selectedFile.size === 0) {
      setError("That file is empty.");
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const document = await uploadDocument(selectedFile);

      onUploadSuccess(document);
      setSuccessMessage(`"${document.filename}" uploaded successfully.`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      // finally runs on success and failure, so the button can never get
      // stuck in the "Uploading…" state.
      setIsUploading(false);
    }
  }

  return (
    <section className="card">
      <h2 className="card-title">Document Management</h2>
      <p className="card-subtitle">
        Upload a PDF. It is validated and stored on the backend.
      </p>

      <div className="upload-controls">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          disabled={isUploading}
          className="upload-input"
          aria-label="Choose a PDF file"
        />
        <button
          type="button"
          className="button"
          onClick={handleUpload}
          disabled={isUploading || !selectedFile}
        >
          {isUploading ? "Uploading…" : "Upload"}
        </button>
      </div>

      {selectedFile && !isUploading && (
        <p className="upload-selected">
          Selected: <strong>{selectedFile.name}</strong> (
          {formatFileSize(selectedFile.size)})
        </p>
      )}

      {isUploading && (
        <div className="upload-progress" role="status">
          <div className="upload-progress-bar" />
        </div>
      )}

      {error && <p className="message message--error">{error}</p>}
      {successMessage && (
        <p className="message message--success">{successMessage}</p>
      )}
    </section>
  );
}

export default DocumentUpload;
