# RAGLab

An educational, production-style **Retrieval-Augmented Generation** application,
built milestone by milestone to learn RAG, Python, React, APIs, vector
databases, embeddings, retrieval, reranking and evaluation from the ground up.

> **Current status: Step 1 — Project Foundation.**
> A working full-stack skeleton: a FastAPI backend with a health endpoint, and
> a React frontend that calls it and displays the result. No RAG features yet.

---

## Tech stack

| Layer    | Choice                                            |
| -------- | ------------------------------------------------- |
| Frontend | React 19, Vite, JavaScript, plain CSS             |
| Backend  | Python, FastAPI, Pydantic, Uvicorn                |
| Planned  | ChromaDB, Sentence Transformers, xAI Grok API     |

---

## Project structure

```
raglab/
├── backend/
│   ├── app/
│   │   ├── main.py              # app setup: CORS, routers, error handler
│   │   ├── api/
│   │   │   └── health.py        # GET /api/health route
│   │   ├── core/
│   │   │   └── config.py        # settings read from environment variables
│   │   ├── models/
│   │   │   └── health.py        # Pydantic response model
│   │   └── services/
│   │       └── health_service.py # health logic (no HTTP knowledge)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # all fetch calls to the backend
│   │   ├── components/
│   │   │   ├── HealthStatus.jsx # loading / error / success UI
│   │   │   └── HealthStatus.css
│   │   ├── App.jsx              # page shell
│   │   ├── App.css
│   │   ├── index.css            # global styles + CSS variables
│   │   └── main.jsx             # React entry point
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── .env.example
├── prompts/
├── .env.example
├── .gitignore
└── README.md
```

---

## Getting started

### 1. Backend

```bash
cd backend

# create the virtual environment (once)
python -m venv venv

# activate it
venv\Scripts\activate        # Windows PowerShell / CMD
source venv/bin/activate     # macOS / Linux / Git Bash

# install dependencies (once, and whenever requirements.txt changes)
pip install -r requirements.txt

# optional: create your own config
cp .env.example .env

# run the server
uvicorn app.main:app --reload --port 8000
```

The backend is now at **http://localhost:8000**, with interactive API docs at
**http://localhost:8000/docs**.

### 2. Frontend

In a **second terminal**:

```bash
cd frontend

# install dependencies (once)
npm install

# optional: create your own config
cp .env.example .env

# run the dev server
npm run dev
```

The frontend is now at **http://localhost:5173**.

---

## Verifying it works

**Health endpoint directly:**

```bash
curl http://localhost:8000/api/health
```

Expected:

```json
{
  "status": "ok",
  "service": "RAGLab API",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-08-11T05:25:23.813646+00:00"
}
```

**React ↔ FastAPI connection:** open http://localhost:5173. You should see a
green dot with *"Backend connected"* and the values returned by the API. Open
DevTools → Network to watch the `health` request; open the backend terminal to
see the matching `GET /api/health 200 OK` log line.

**Failure path:** stop the backend and click *Check again*. The dot turns red
and a readable error appears instead of a blank screen.

---

## API reference (Step 1)

| Method | Path          | Description                    |
| ------ | ------------- | ------------------------------ |
| GET    | `/`           | Service info and doc links     |
| GET    | `/api/health` | Backend health check           |
| GET    | `/docs`       | Interactive Swagger UI         |

---

## Configuration

No secrets are required in Step 1. Configuration is read from environment
variables; `.env` files are git-ignored and only `.env.example` is committed.

| Variable               | Where    | Purpose                             |
| ---------------------- | -------- | ----------------------------------- |
| `APP_NAME`             | backend  | Service name in docs and health     |
| `APP_VERSION`          | backend  | Version in health response          |
| `ENVIRONMENT`          | backend  | `development` / `production`        |
| `CORS_ALLOWED_ORIGINS` | backend  | Comma-separated allowed frontends   |
| `VITE_API_BASE_URL`    | frontend | Base URL of the backend             |

⚠️ `VITE_*` variables are bundled into the browser build — never put a secret
in the frontend `.env`.

---

## Architecture notes

**Layered backend.** A request flows
`api/ (HTTP) → services/ (logic) → models/ (shape)`, with `core/` holding
configuration. The service layer imports no FastAPI code, so logic stays
testable and later milestones can reuse it from scripts or background jobs.

**One place for network code.** The frontend does all fetching through
`src/api/client.js`, which normalises errors into readable messages. Components
never call `fetch` directly.

**Explicit request states.** `HealthStatus.jsx` models loading, error and
success as three separate states — the same pattern every later data screen
(upload, search, chat) will follow.

---

## Roadmap

- [x] **Step 1** — Project foundation: full-stack skeleton + health check
- [ ] **Step 2** — *not started; awaiting instructions*
