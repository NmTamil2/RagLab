/**
 * Thin wrapper around fetch for talking to the RAGLab backend.
 *
 * Everything network-related lives here so React components stay focused on
 * rendering. Future milestones (upload, search, chat) add functions here.
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
 * @returns {Promise<any>}
 */
async function request(path) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`);
  } catch {
    // fetch only rejects for network-level problems: server down, DNS, CORS.
    throw new Error(
      `Cannot reach the backend at ${API_BASE_URL}. Is it running?`,
    );
  }

  if (!response.ok) {
    // The server answered, but with an error status (4xx / 5xx).
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // Body was not JSON — keep the status-based message.
    }
    throw new Error(`Backend returned an error: ${detail}`);
  }

  return response.json();
}

/**
 * GET /api/health — ask the backend whether it is alive.
 * @returns {Promise<{status: string, service: string, version: string,
 *                    environment: string, timestamp: string}>}
 */
export function fetchHealth() {
  return request("/api/health");
}

export { API_BASE_URL };
