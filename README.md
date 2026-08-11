# RAGLab

An educational, production-style **Retrieval-Augmented Generation** application,
built milestone by milestone to learn RAG, Python, React, APIs, vector
databases, embeddings, retrieval, reranking and evaluation from the ground up.

> **Current status: Step 2 — Document Upload.**
> A full-stack skeleton with a health check, plus PDF upload: React sends a
> file to FastAPI, which validates it, stores it on disk and returns metadata.
> No text extraction, embeddings or retrieval yet.

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
│   │   ├── main.py                   # app setup: CORS, routers, error handler
│   │   ├── api/
│   │   │   ├── health.py             # GET /api/health
│   │   │   └── documents.py          # POST /api/documents/upload
│   │   ├── core/
│   │   │   └── config.py             # settings read from environment variables
│   │   ├── models/
│   │   │   ├── health.py             # Pydantic response models
│   │   │   └── document.py
│   │   └── services/
│   │       ├── health_service.py     # logic layer (no HTTP knowledge)
│   │       └── document_service.py   # validation + file storage
│   ├── storage/documents/            # uploaded PDFs (git-ignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js             # all fetch calls to the backend
│   │   ├── components/
│   │   │   ├── HealthStatus.jsx      # loading / error / success UI
│   │   │   ├── DocumentUpload.jsx    # file picker + upload states
│   │   │   ├── DocumentList.jsx      # uploaded documents
│   │   │   └── *.css
│   │   ├── utils/formatFileSize.js   # bytes -> "1.4 MB"
│   │   ├── App.jsx                   # page shell, owns document list state
│   │   ├── App.css
│   │   ├── index.css                 # tokens + shared .card/.button/.message
│   │   └── main.jsx                  # React entry point
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

**Upload:** choose a PDF in the Document Management panel and click *Upload*.
It should appear in the Uploaded Documents list with its size and ID, and the
file should exist as `backend/storage/documents/<document_id>.pdf`. Try a
`.txt` file too — it must be rejected with a readable message.

---

## API reference (Step 1)

| Method | Path                     | Description                |
| ------ | ------------------------ | -------------------------- |
| GET    | `/`                      | Service info and doc links |
| GET    | `/api/health`            | Backend health check       |
| POST   | `/api/documents/upload`  | Upload a PDF (form field `file`) |
| GET    | `/docs`                  | Interactive Swagger UI     |

Upload example:

```bash
curl -F "file=@mydoc.pdf" http://localhost:8000/api/documents/upload
```

```json
{
  "document_id": "c15d9432-bb14-43de-a5ba-f0cdf3829cd6",
  "filename": "mydoc.pdf",
  "file_type": "pdf",
  "file_size": 102400,
  "uploaded_at": "2026-08-11T09:31:42.978806+00:00"
}
```

Error responses use `{"detail": "..."}`:

| Status | When                                          |
| ------ | --------------------------------------------- |
| 400    | Not a PDF, empty file, or missing filename    |
| 413    | Larger than `MAX_UPLOAD_SIZE_MB`              |
| 422    | No `file` field in the request                |
| 500    | Valid file, but the disk write failed         |

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
| `DOCUMENTS_DIR`        | backend  | Where uploaded PDFs are stored      |
| `MAX_UPLOAD_SIZE_MB`   | backend  | Upload size ceiling                 |
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

**Explicit request states.** `HealthStatus.jsx` and `DocumentUpload.jsx` both
model loading, error and success as separate states — the same pattern every
later data screen (search, chat) will follow.

**Uploads are streamed, not buffered.** `document_service.py` reads the file in
1 MB chunks and checks the size limit as it goes, so memory use stays flat and
an oversized upload is rejected partway through rather than after it has fully
arrived. A rejected upload's partial file is always deleted.

**Stored filenames are server-generated.** A file is saved as
`<uuid>.pdf`, never under the name the user supplied. This prevents two
problems at once: collisions when two people upload `report.pdf`, and path
traversal, where a filename like `../../app/main.py` could overwrite source
code. The original name is kept in the response metadata only.

**PDFs are verified by content, not by name.** The service checks that the file
starts with the `%PDF-` magic bytes, so a renamed `.exe` is rejected even though
its name ends in `.pdf`.

---

## Roadmap

- [x] **Step 1** — Project foundation: full-stack skeleton + health check
- [x] **Step 2** — Document upload: PDF validation and local file storage
- [ ] **Step 3** — *not started; awaiting instructions*
