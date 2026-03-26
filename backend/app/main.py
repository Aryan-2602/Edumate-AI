import logging
import time
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import create_tables, engine
from app.rate_limit import limiter
from app import telemetry
from app.api import auth, documents, ai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting EduMate-AI Backend...")
    telemetry.init_wandb()

    if settings.sentry_dsn:
        try:
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[FastApiIntegration()],
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
            )
            logger.info("Sentry initialized successfully")
        except Exception as e:
            logger.warning("Failed to initialize Sentry: %s", e)

    try:
        create_tables()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error("Failed to create database tables: %s", e)
        raise

    yield

    logger.info("Shutting down EduMate-AI Backend...")
    telemetry.finish_wandb()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered educational platform for interactive learning",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://edumate-ai.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "testserver",  # FastAPI TestClient default host
        "*.vercel.app",
        "*.amazonaws.com",
        "*.elasticbeanstalk.com",
    ],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "Something went wrong",
        },
    )


@app.get("/health")
async def health_check():
    """Liveness: process is up."""
    return {
        "status": "healthy",
        "service": "edumate-ai-backend",
        "version": settings.app_version,
        "timestamp": time.time(),
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness: dependencies required for traffic."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "ok",
        }
    except Exception as e:
        logger.warning("Readiness check failed: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "unready", "database": "error", "detail": str(e)},
        )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "Welcome to EduMate-AI Backend",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "health": "/health",
        "ready": "/health/ready",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
