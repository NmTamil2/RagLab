import HealthStatus from "./components/HealthStatus";
import "./App.css";

/**
 * Root component: the page shell.
 *
 * Step 1 shows only the project identity and the backend connection state.
 * Later milestones will add upload, search and chat sections here.
 */
function App() {
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
      </main>

      <footer className="app-footer">Step 1 — Project foundation</footer>
    </div>
  );
}

export default App;
