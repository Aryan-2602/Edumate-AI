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
- Deployment: AWS Fargate

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
```

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

# Apply migrations (recommended for Postgres)
alembic upgrade head

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