import { useState } from "react";
import { extractDocumentText } from "../api/client";
import "./DocumentExtract.css";

/**
 * "Extract Text" action and result view for one uploaded document.
 *
 * @param {{ documentId: string }} props
 *
 * Each document gets its own instance, so extraction state (loading, error,
 * pages) stays local to the document it belongs to. Two documents can be
 * extracted independently without one's spinner or error affecting the other.
 */
function DocumentExtract({ documentId }) {
  const [isExtracting, setIsExtracting] = useState(false);
  const [extraction, setExtraction] = useState(null);
  const [error, setError] = useState(null);

  async function handleExtract() {
    setIsExtracting(true);
    // Clear the previous outcome so the user never sees a stale error next to
    // fresh results, or old pages next to a new failure.
    setError(null);
    setExtraction(null);

    try {
      setExtraction(await extractDocumentText(documentId));
    } catch (extractionError) {
      setError(extractionError.message);
    } finally {
      setIsExtracting(false);
    }
  }

  return (
    <div className="extract">
      <button
        type="button"
        className="button button--small"
        onClick={handleExtract}
        disabled={isExtracting}
      >
        {isExtracting ? "Extracting…" : extraction ? "Extract again" : "Extract Text"}
      </button>

      {isExtracting && (
        <p className="extract-status" role="status">
          Reading the PDF page by page…
        </p>
      )}

      {error && <p className="message message--error">{error}</p>}

      {extraction && (
        <div className="extract-result">
          <p className="extract-summary">
            Extracted <strong>{extraction.page_count}</strong>{" "}
            {extraction.page_count === 1 ? "page" : "pages"}
          </p>

          <ol className="page-list">
            {extraction.pages.map((page) => (
              <li key={page.page_number} className="page">
                <h4 className="page-number">Page {page.page_number}</h4>
                {/* <pre> keeps the line breaks the PDF actually had. */}
                {page.text ? (
                  <pre className="page-text">{page.text}</pre>
                ) : (
                  <p className="page-empty">No text on this page.</p>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export default DocumentExtract;
