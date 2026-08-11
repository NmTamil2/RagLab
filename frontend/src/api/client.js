/**
 * Thin wrapper around fetch for talking to the RAGLab backend.
 *
 * Everything network-related lives here so React components stay focused on
 * rendering. Future milestones (search, chat) add functions here.
 */

// Vite exposes variables from .env that start with VITE_ on import.meta.env.
// The fallback keeps the app working before you create a .env file.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * Call the backend and return parsed JSON.
 * Throws an Error with a readable message when anything goes wrong.
 *
 * @param {string} path - path starting with a slash, e.g. "/api/health"
 * @param {RequestInit} [options] - extra fetch options (method, body, ...)
 * @returns {Promise<any>}
 */
async function request(path, options) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    // fetch only rejects for network-level problems: server down, DNS, CORS.
    throw new Error(
      `Cannot reach the backend at ${API_BASE_URL}. Is it running?`,
    );
  }

  if (!response.ok) {
    // The server answered, but with an error status (4xx / 5xx).
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

/**
 * Pull the clearest possible message out of an error response.
 *
 * FastAPI replies with {"detail": "..."} for our own HTTPExceptions, but with
 * {"detail": [{...}, ...]} for automatic validation errors, so both shapes
 * have to be handled.
 *
 * @param {Response} response
 * @returns {Promise<string>}
 */
async function readErrorMessage(response) {
  try {
    const body = await response.json();
    const detail = body?.detail;

    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  } catch {
    // Body was not JSON — fall through to the status-based message.
  }

  return `Backend returned an error: ${response.status} ${response.statusText}`;
}

/**
 * GET /api/health — ask the backend whether it is alive.
 * @returns {Promise<{status: string, service: string, version: string,
 *                    environment: string, timestamp: string}>}
 */
export function fetchHealth() {
  return request("/api/health");
}

/**
 * POST /api/documents/upload — send a PDF to the backend.
 *
 * @param {File} file - the file chosen in the <input type="file">
 * @returns {Promise<{document_id: string, filename: string, file_type: string,
 *                    file_size: number, uploaded_at: string}>}
 */
export function uploadDocument(file) {
  // FormData is how a file is sent over HTTP. The field name "file" must match
  // the parameter name in the FastAPI route.
  const formData = new FormData();
  formData.append("file", file);

  // Note: we deliberately do NOT set a Content-Type header. The browser must
  // set it itself, because it has to append the multipart boundary marker.
  return request("/api/documents/upload", {
    method: "POST",
    body: formData,
  });
}

export { API_BASE_URL };
