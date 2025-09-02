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
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
