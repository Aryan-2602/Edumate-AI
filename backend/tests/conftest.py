"""Pytest setup: test env before app import."""

from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-ci")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_edumate.db")
os.environ.setdefault("S3_VERIFY_BUCKET_ON_INIT", "false")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("LOCAL_STORAGE_ROOT", "./.pytest_storage")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def settings():
    from app.config import settings as s

    return s


@pytest.fixture()
def db_session(settings):
    from app.database import Base

    engine = create_engine(settings.database_url)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
