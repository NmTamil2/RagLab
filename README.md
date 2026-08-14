# RAGLab

An educational, production-style **Retrieval-Augmented Generation** application,
built milestone by milestone to learn RAG, Python, React, APIs, vector
databases, embeddings, retrieval, reranking and evaluation from the ground up.

> **Current status: Step 4 — Document Chunking.**
> A full-stack skeleton with a health check, PDF upload, page-by-page text
> extraction, and character-based chunking: page text is cut into small
> overlapping pieces that each remember their document, page and position.
> No embeddings, vector database or retrieval yet.

---

## Tech stack

| Layer    | Choice                                            |
| -------- | ------------------------------------------------- |
| Frontend | React 19, Vite, JavaScript, plain CSS             |
| Backend  | Python, FastAPI, Pydantic, Uvicorn, PyMuPDF       |
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
│   │   │   └── documents.py          # upload + extract + chunk routes
│   │   ├── core/
│   │   │   └── config.py             # settings read from environment variables
│   │   ├── models/
│   │   │   ├── health.py             # Pydantic response models
│   │   │   ├── document.py           # upload metadata + extraction models
│   │   │   └── chunk.py              # chunk + chunking-result models
│   │   └── services/
│   │       ├── health_service.py     # logic layer (no HTTP knowledge)
│   │       ├── document_service.py   # validation + file storage + lookup
│   │       ├── document_parser.py    # PyMuPDF page-by-page text extraction
│   │       └── chunking_service.py   # character-based sliding-window chunking
│   ├── tests/
│   │   ├── test_document_parser.py   # parser tests (pytest)
│   │   └── test_chunking_service.py  # chunking tests (pytest)
│   ├── storage/documents/            # uploaded PDFs + metadata (git-ignored)
│   ├── pytest.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js             # all fetch calls to the backend
│   │   ├── components/
│   │   │   ├── HealthStatus.jsx      # loading / error / success UI
│   │   │   ├── DocumentUpload.jsx    # file picker + upload states
│   │   │   ├── DocumentList.jsx      # uploaded documents
│   │   │   ├── DocumentExtract.jsx   # Extract Text button + page view
│   │   │   ├── DocumentChunks.jsx    # Chunk Document button + chunk preview
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

### 3. Backend tests

From `backend/`, with the virtual environment active:

```bash
pytest
```

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
  "version": "0.4.0",
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

**Extract:** click *Extract Text* under an uploaded document. The page count
appears, followed by each page's text under its own numbered heading. A blank
page is shown as *"No text on this page."* rather than being skipped.

**Chunk:** click *Chunk Document*. The chunk count and the `chunk_size` /
`chunk_overlap` used appear, followed by the chunks themselves — each with its
index, page number, ID and length. Compare the end of one chunk with the start
of the next: the last `chunk_overlap` characters repeat. Change `CHUNK_SIZE` in
`backend/.env`, restart the backend, and click again to see the difference.

---

## API reference

| Method | Path                                    | Description                      |
| ------ | --------------------------------------- | -------------------------------- |
| GET    | `/`                                     | Service info and doc links       |
| GET    | `/api/health`                           | Backend health check             |
| POST   | `/api/documents/upload`                 | Upload a PDF (form field `file`) |
| POST   | `/api/documents/{document_id}/extract`  | Extract text, page by page       |
| POST   | `/api/documents/{document_id}/chunk`    | Split the text into chunks       |
| GET    | `/docs`                                 | Interactive Swagger UI           |

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

Extract example:

```bash
curl -X POST http://localhost:8000/api/documents/c15d9432-bb14-43de-a5ba-f0cdf3829cd6/extract
```

```json
{
  "document_id": "c15d9432-bb14-43de-a5ba-f0cdf3829cd6",
  "filename": "mydoc.pdf",
  "page_count": 3,
  "pages": [
    { "page_number": 1, "text": "ADAS Overview\nAdvanced Driver Assistance..." },
    { "page_number": 2, "text": "" },
    { "page_number": 3, "text": "Chapter 2\nSensor fusion combines..." }
  ]
}
```

Chunk example — the two query parameters are optional and default to the
configured `CHUNK_SIZE` / `CHUNK_OVERLAP`, so settings can be compared without
restarting the server:

```bash
curl -X POST "http://localhost:8000/api/documents/c15d9432-.../chunk"
curl -X POST "http://localhost:8000/api/documents/c15d9432-.../chunk?chunk_size=300&chunk_overlap=30"
```

```json
{
  "document_id": "c15d9432-bb14-43de-a5ba-f0cdf3829cd6",
  "filename": "mydoc.pdf",
  "page_count": 3,
  "chunk_count": 5,
  "chunk_size": 500,
  "chunk_overlap": 50,
  "chunks": [
    {
      "chunk_id": "c15d9432-bb14-43de-a5ba-f0cdf3829cd6-p1-c0",
      "document_id": "c15d9432-bb14-43de-a5ba-f0cdf3829cd6",
      "page_number": 1,
      "chunk_index": 0,
      "char_count": 500,
      "text": "ADAS Overview Advanced driver assistance systems ..."
    }
  ]
}
```

Error responses use `{"detail": "..."}`:

| Status | When                                                                    |
| ------ | ----------------------------------------------------------------------- |
| 400    | Upload: not a PDF, empty file, or missing filename. Chunk: `chunk_size` ≤ 0, negative `chunk_overlap`, or overlap ≥ size |
| 404    | Extract/chunk: unknown document ID, or its stored file is gone          |
| 413    | Upload: larger than `MAX_UPLOAD_SIZE_MB`                                |
| 422    | Upload: no `file` field. Extract/chunk: corrupt, encrypted or no text    |
| 500    | Disk write failed, or the parser failed unexpectedly                    |

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
| `CHUNK_SIZE`           | backend  | Characters per chunk                |
| `CHUNK_OVERLAP`        | backend  | Characters repeated between chunks  |
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

**Page numbers are never lost.** `document_parser.py` returns one record per
page, and pages with no text are kept as empty entries instead of being
dropped. If a blank page were skipped, every page after it would be misnumbered
— and page numbers are what later milestones use for chunk metadata, retrieval
results and citations.

**Only one module knows about PyMuPDF.** `document_parser.py` is the sole
importer of `pymupdf`. Routes deal in paths and models, so swapping the PDF
library later would touch one file.

**Document IDs from the URL are validated as UUIDs** before being used to build
a filesystem path, so a crafted ID cannot escape the storage folder.

**Chunks stay inside one page.** Each page is chunked on its own, so a chunk
never contains text from two pages and `page_number` is one exact number rather
than a range. The alternative — joining the whole document into one string and
sliding a window over it — produces slightly better chunks at page breaks, but
every chunk that crosses a boundary then needs a *list* of pages, and every
consumer of that metadata (retrieval display, citations, evaluation) has to
decide which of them to show a user. Exact page numbers are worth more right now
than perfect prose at page boundaries, and this is the reversible choice: making
chunks span pages later is a change to one function, while recovering a page
number that was never recorded is impossible.

**Chunk size and overlap are configuration, not constants.** They live in
`Settings`, arrive at the chunker as a validated `ChunkingConfig` object, and
are echoed back in every response. The chunking functions never read `settings`
themselves, which is why the tests can drive them with any values. Invalid
combinations are rejected in the `ChunkingConfig` constructor, so an unusable
config cannot exist anywhere in the system — and an overlap that is not smaller
than the chunk size (which would make chunking loop forever) stops the server at
startup rather than at request time.

**Chunk IDs are derived, not random.** `<document_id>-p<page>-c<index>` is
readable in the UI and stable: re-chunking a document with the same settings
produces the same IDs, so re-running will overwrite rather than duplicate when
chunks reach a vector store.

**The original filename lives in a sidecar JSON file** next to each stored PDF,
because uploads are renamed to `<uuid>.pdf` and the PDF itself cannot tell us
what the user called it. A real database replaces this in a later milestone; if
the sidecar is missing, the lookup falls back to what the file itself knows.

---

## Roadmap

- [x] **Step 1** — Project foundation: full-stack skeleton + health check
- [x] **Step 2** — Document upload: PDF validation and local file storage
- [x] **Step 3** — PDF parsing: page-by-page text extraction with PyMuPDF
- [x] **Step 4** — Document chunking: configurable character-based chunks with
      page metadata
- [ ] **Step 5** — *not started; awaiting instructions*
