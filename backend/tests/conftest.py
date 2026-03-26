"""Pytest setup: test env before app import."""

from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-for-ci")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_edumate.db")
os.environ.setdefault("S3_VERIFY_BUCKET_ON_INIT", "false")
