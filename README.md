# EduMate-AI

A backend-first LLM workflow system for document-based question answering, quiz generation, and flashcard creation using retrieval-augmented pipelines.

## 🚀 Overview

EduMate-AI processes user-uploaded documents and exposes modular AI workflows for:

- Question answering (RAG)
- Quiz generation
- Flashcard generation

The system is designed with deterministic routing, validation guardrails, and observable backend services, making it reliable and production-oriented rather than a simple chatbot demo.

## 🧠 Workflow Architecture

The backend is structured as modular, deterministic workflows:

### 1. RAG Workflow (Q&A)

Input → Retrieval (Chroma) → Context Validation → LLM Generation → Post-processing

### 2. Quiz Workflow

Document Content → Validation → Structured LLM Generation → JSON Parsing → Persistence

### 3. Flashcard Workflow

Document Content → Validation → LLM Generation → Storage in PostgreSQL

## 🔀 Intent Routing

A lightweight router selects workflows based on explicit intent:

- `qa`
- `quiz`
- `flashcards`

Keyword-based fallback is used for robustness.

## 🛡️ Guardrails

- Retrieval filtered by `document_id` and `user_id`
- Context validation before generation
- Safe fallback responses when context is weak
- Structured parsing for quiz outputs

## 📊 Observability

- Request tracing via `X-Request-ID`
- Stage-level logging (retrieval, generation, latency)
- Health and readiness endpoints

## 🏗️ Architecture

### Backend (Primary Focus)

- Framework: FastAPI (Python 3.11+)
- LLM Stack: OpenAI GPT-4 via LangChain
- Vector Store: Chroma (document-scoped retrieval)
- Database: PostgreSQL (documents, quizzes, flashcards, progress)
- Storage: AWS S3
- Migrations: Alembic
- Deployment: AWS 

### Frontend (Minimal)

- Framework: Next.js 14 + React 18
- Auth: Firebase (Google OAuth)
- Used for basic interaction; primary focus is backend workflows

## 🛠️ Tech Stack

| Layer | Technologies |
|------|--------------|
| Backend | FastAPI, Python, SQLAlchemy |
| LLM / AI | OpenAI GPT-4, LangChain |
| Retrieval | Chroma (vector search) |
| Storage | AWS S3 |
| Database | PostgreSQL |
| Infra | AWS (Fargate, RDS), Vercel |
| Monitoring | Sentry, W&B, CloudWatch |
| CI/CD | GitHub Actions |

## 📁 Project Structure

```
backend/
  app/
    api/          # FastAPI routes
    workflows/    # RAG, quiz, flashcard pipelines
    services/     # Retrieval, generation, storage
    guards/       # Validation and fallback logic
    routing/      # Intent router
    database.py
  alembic/        # DB migrations
  requirements.txt

frontend/
  src/

infrastructure/
.github/
data/             # optional: keep local PDFs here (gitignored); see below
```

### Sample textbook (local)

Place PDFs you want to test with under `data/` (for example `data/Mathematics-Textbook-Grade-5.pdf`). That folder is **gitignored** so large files stay on your machine.

The backend does **not** watch or auto-import files from `data/`. To use a PDF in workflows, **upload** it through the API (`POST /api/v1/documents/upload`) or the frontend demo at `/demo` after S3 and auth are configured. Wait until `processing_status` is `completed`, then run ask / quiz / flashcards against the returned `document_id`.

## 🔄 Example Flow

1. User uploads document → stored in S3 and chunked into embeddings
2. Query sent with intent (`qa`, `quiz`, `flashcards`)
3. Router selects workflow
4. Retrieval filtered by document + user
5. Context validated before LLM
6. LLM generates output
7. Output validated, stored, and returned

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Postgres / staging: apply migrations
# alembic upgrade head
#
# Local SQLite: tables are created automatically on startup (no Alembic needed for a fresh file—see "Local SQLite database" below).

uvicorn app.main:app --reload
```

### Frontend Setup (Optional)

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy the template:

```bash
cp .env.example backend/.env
cp .env.example frontend/.env.local
```

Minimum required (backend):

```bash
DATABASE_URL=sqlite:///./edumate.db
OPENAI_API_KEY=your_key
```

### Local SQLite database

- **No separate SQLite server** is required; Python creates a file (e.g. `backend/edumate.db`) when the app connects.
- **Schema** is created on startup via SQLAlchemy `create_tables()` (see `app/main.py` lifespan). After `cp .env.example backend/.env` and setting `DATABASE_URL` / `OPENAI_API_KEY`, run `uvicorn` from `backend/` once; the file and tables appear automatically.
- **Verify**: `GET /health/ready` should report `database: ok`. Optionally: `sqlite3 edumate.db ".tables"` from `backend/`.
- **Alembic**: Existing revisions are additive on top of an implied base schema. Do **not** run `alembic upgrade head` on an empty database (migrations expect tables to exist). If you already have a full schema from `create_tables()`, `alembic upgrade head` may fail with duplicate-column errors. For local SQLite dev, rely on `create_tables()`; only use `alembic stamp head` if you intentionally want to mark the DB without running SQL (advanced).

## 🧪 Development

### Run Tests

```bash
cd backend
pytest
```

## ⚠️ Limitations

- Frontend is minimal and primarily for demonstration
- Legacy embeddings may require reprocessing for strict filtering
- Ingestion runs asynchronously after upload in-process (FastAPI background task)
- Retrieval quality depends on chunking and embedding strategy

## 🎯 Design Goals

- Modular and deterministic LLM workflows
- Reliable, explainable retrieval pipelines
- Backend-first architecture
- Production-aware design (logging, migrations, health checks)

## 📄 License

MIT License