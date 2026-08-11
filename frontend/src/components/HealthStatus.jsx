import { useCallback, useEffect, useState } from "react";
import { API_BASE_URL, fetchHealth } from "../api/client";
import "./HealthStatus.css";

/**
 * Shows whether the React app can reach the FastAPI backend.
 *
 * It models the request as three explicit states — loading, error, success —
 * which is the same pattern every later data-fetching screen will use.
 */
function HealthStatus() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // useCallback keeps the same function identity across renders, so the
  // effect below does not re-run on every render.
  const checkHealth = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err) {
      setHealth(null);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Run once when the component first appears on screen.
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const state = isLoading ? "loading" : error ? "error" : "ok";
  const label = {
    loading: "Checking backend…",
    error: "Backend unreachable",
    ok: "Backend connected",
  }[state];

  return (
    <section className="card">
      <div className="health-header">
        <span className={`status-dot status-dot--${state}`} aria-hidden="true" />
        <h2 className="card-title">{label}</h2>
      </div>

      {state === "ok" && (
        <dl className="health-details">
          <dt>Status</dt>
          <dd>{health.status}</dd>
          <dt>Service</dt>
          <dd>{health.service}</dd>
          <dt>Version</dt>
          <dd>{health.version}</dd>
          <dt>Environment</dt>
          <dd>{health.environment}</dd>
          <dt>Checked at</dt>
          <dd>{new Date(health.timestamp).toLocaleTimeString()}</dd>
        </dl>
      )}

      {state === "error" && <p className="message message--error">{error}</p>}

      <div className="health-footer">
        <button
          type="button"
          className="button"
          onClick={checkHealth}
          disabled={isLoading}
        >
          {isLoading ? "Checking…" : "Check again"}
        </button>
        <code className="health-endpoint">{API_BASE_URL}/api/health</code>
      </div>
    </section>
  );
}

export default HealthStatus;
