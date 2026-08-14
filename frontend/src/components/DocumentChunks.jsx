import { useState } from "react";
import { chunkDocument } from "../api/client";
import "./DocumentChunks.css";

/**
 * How many chunks to render before asking the user to opt in to the rest.
 *
 * A long PDF can produce hundreds of chunks, and putting them all in the DOM at
 * once makes the page crawl. Twenty is enough to see the pattern — including
 * the first page boundary — and the count above always states the true total,
 * so nothing is hidden without saying so.
 */
const PREVIEW_LIMIT = 20;

/**
 * "Chunk Document" action and chunk preview for one uploaded document.
 *
 * @param {{ documentId: string }} props
 *
 * The same shape as DocumentExtract: local loading / error / result state, one
 * instance per document, so two documents never interfere with each other.
 */
function DocumentChunks({ documentId }) {
  const [isChunking, setIsChunking] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showAll, setShowAll] = useState(false);

  async function handleChunk() {
    setIsChunking(true);
    // Clear the previous outcome so fresh results are never shown next to a
    // stale error, and collapse the list again for the new run.
    setError(null);
    setResult(null);
    setShowAll(false);

    try {
      setResult(await chunkDocument(documentId));
    } catch (chunkingError) {
      setError(chunkingError.message);
    } finally {
      setIsChunking(false);
    }
  }

  const visibleChunks =
    result && !showAll ? result.chunks.slice(0, PREVIEW_LIMIT) : result?.chunks;

  const hiddenCount = result ? result.chunks.length - (visibleChunks?.length ?? 0) : 0;

  return (
    <div className="chunks">
      <button
        type="button"
        className="button button--small"
        onClick={handleChunk}
        disabled={isChunking}
      >
        {isChunking ? "Chunking…" : result ? "Chunk again" : "Chunk Document"}
      </button>

      {isChunking && (
        <p className="chunks-status" role="status">
          Splitting the text into chunks…
        </p>
      )}

      {error && <p className="message message--error">{error}</p>}

      {result && (
        <div className="chunks-result">
          <p className="chunks-summary">
            Generated <strong>{result.chunk_count}</strong>{" "}
            {result.chunk_count === 1 ? "chunk" : "chunks"} from{" "}
            {result.page_count} {result.page_count === 1 ? "page" : "pages"}
          </p>

          {/* The settings that produced these chunks, echoed from the API
              rather than hard-coded here — so the display cannot disagree
              with what the backend actually did. */}
          <dl className="chunks-config">
            <div className="chunks-config-item">
              <dt>chunk_size</dt>
              <dd>{result.chunk_size}</dd>
            </div>
            <div className="chunks-config-item">
              <dt>chunk_overlap</dt>
              <dd>{result.chunk_overlap}</dd>
            </div>
          </dl>

          {result.chunk_count === 0 ? (
            <p className="chunks-empty">
              This document produced no chunks — none of its pages held text.
            </p>
          ) : (
            <>
              <ol className="chunk-list">
                {visibleChunks.map((chunk) => (
                  <li key={chunk.chunk_id} className="chunk">
                    <div className="chunk-header">
                      <span className="chunk-label">
                        Chunk {chunk.chunk_index}
                      </span>
                      <span className="chunk-fact">
                        Page {chunk.page_number}
                      </span>
                      <span className="chunk-fact">
                        Length {chunk.char_count}
                      </span>
                    </div>
                    <p className="chunk-id" title={chunk.chunk_id}>
                      {chunk.chunk_id}
                    </p>
                    <p className="chunk-text">{chunk.text}</p>
                  </li>
                ))}
              </ol>

              {hiddenCount > 0 && (
                <button
                  type="button"
                  className="button button--small chunks-more"
                  onClick={() => setShowAll(true)}
                >
                  Show {hiddenCount} more {hiddenCount === 1 ? "chunk" : "chunks"}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default DocumentChunks;
