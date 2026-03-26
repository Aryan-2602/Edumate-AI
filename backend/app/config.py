from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    app_name: str = "EduMate-AI Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/edumate"

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7

    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = "edumate-ai-documents"
    # If False, skip head_bucket at startup (upload may still fail if misconfigured)
    s3_verify_bucket_on_init: bool = True

    # Firebase
    firebase_project_id: Optional[str] = None
    firebase_private_key_id: Optional[str] = None
    firebase_private_key: Optional[str] = None
    firebase_client_email: Optional[str] = None
    firebase_client_id: Optional[str] = None

    # Vector Database
    chroma_persist_directory: str = "./chroma_db"

    # Monitoring
    sentry_dsn: Optional[str] = None
    wandb_project: str = "edumate-ai"
    wandb_api_key: Optional[str] = None
    # In-memory workflow metrics ring buffer + diagnostics (opt-in)
    workflow_metrics_max_samples: int = 2000
    enable_workflow_metrics_endpoint: bool = False
    # If set, GET /diagnostics/workflow-metrics* requires header X-Admin-Metrics-Key
    metrics_admin_key: Optional[str] = None

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Guardrails
    max_upload_bytes: int = 26214400  # 25 MiB
    rag_top_k_max: int = 50
    rag_top_k_default: int = 5
    quiz_questions_max: int = 20
    quiz_questions_default: int = 5
    flashcards_max: int = 50
    flashcards_default: int = 10
    question_max_length: int = 8000
    openai_request_timeout: float = 120.0
    rate_limit_default: str = "120/minute"
    rate_limit_ai_write: str = "30/minute"
    rate_limit_upload: str = "20/minute"
    content_join_max_chars: int = 120000

    # RAG guards (retrieval-before-generation + answer checks).
    rag_guard_min_chunks: int = 1
    rag_guard_min_context_chars: int = 40
    rag_guard_max_best_distance: Optional[float] = 2.0
    rag_guard_min_answer_chars: int = 5
    rag_guard_min_context_word_overlap: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
