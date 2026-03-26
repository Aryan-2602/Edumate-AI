"""Shared FastAPI dependencies (singleton services)."""

from functools import lru_cache

from app.services.ai_service import AIService
from app.services.storage_service import StorageService


@lru_cache
def get_ai_service() -> AIService:
    return AIService()


@lru_cache
def get_storage_service() -> StorageService:
    return StorageService()
