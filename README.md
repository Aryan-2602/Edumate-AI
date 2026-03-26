# EduMate-AI

An intelligent educational platform that transforms notes and textbooks into interactive learning experiences using AI-powered Q&A, quizzes, and flashcards.

## 🚀 Features

- **Smart Document Processing**: Upload PDFs and text documents with automatic chunking and embedding
- **AI-Powered Q&A**: Get instant answers to questions using Retrieval-Augmented Generation (RAG)
- **Interactive Learning**: Generate quizzes and flashcards from your study materials
- **Progress Tracking**: Monitor your learning progress and study patterns
- **Real-time Chat**: Interactive chat interface for seamless learning

## 🏗️ Architecture

### Frontend
- **Framework**: Next.js 14 with React 18
- **Styling**: Tailwind CSS + Headless UI components
- **Authentication**: Firebase Auth with Google OAuth
- **Deployment**: Vercel

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI/LLM**: OpenAI GPT-4 via LangChain
- **Vector Database**: Chroma for semantic search
- **File Storage**: AWS S3
- **Database**: PostgreSQL
- **Deployment**: AWS Fargate

### AI Pipeline
- **Document Processing**: PDF/text chunking and embedding generation
- **RAG System**: Vector search + LLM context retrieval
- **Content Generation**: Quizzes, flashcards, and Q&A responses

## 🛠️ Tech Stack

- **Frontend**: Next.js, React, Tailwind CSS, Firebase
- **Backend**: FastAPI, Python, LangChain, Chroma
- **AI/ML**: OpenAI GPT-4, Embeddings
- **Infrastructure**: AWS (S3, EC2/Fargate, RDS), Vercel
- **Monitoring**: Sentry, Weights & Biases, CloudWatch
- **CI/CD**: GitHub Actions

## 📁 Project Structure

```
EduMate-AI/
├── backend/                 # FastAPI backend
│   ├── app/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Next.js frontend
│   ├── src/
│   ├── package.json
│   └── next.config.js
├── infrastructure/          # AWS deployment configs
├── .github/                 # GitHub Actions CI/CD
└── docs/                    # Documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker
- AWS CLI configured
- OpenAI API key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
# Apply DB migrations (production / existing DBs). From backend/: set DATABASE_URL or use .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables
Create `.env.local` in frontend and `.env` in backend:
```bash
# OpenAI
OPENAI_API_KEY=your_key_here

# Firebase
NEXT_PUBLIC_FIREBASE_API_KEY=your_key
FIREBASE_ADMIN_CREDENTIALS=path_to_service_account.json

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/edumate

# Optional: set false for local dev without a real S3 bucket (upload may still fail)
# S3_VERIFY_BUCKET_ON_INIT=false
```

## 🔧 Development

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run test
```

### Building for Production
```bash
# Backend
cd backend
docker build -t edumate-backend .

# Frontend
cd frontend
npm run build
```

## 📊 Monitoring & Analytics

- **Error Tracking**: Sentry integration
- **Performance**: Real-time monitoring with CloudWatch
- **AI Metrics**: Weights & Biases for model tracking
- **User Analytics**: Google Analytics integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For support and questions, please open an issue in the GitHub repository.