from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
import logging
import time
from contextlib import asynccontextmanager

from app.config import settings
from app.database import create_tables
from app.api import auth, documents, ai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting EduMate-AI Backend...")
    
    # Initialize Sentry if configured
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
            logger.warning(f"Failed to initialize Sentry: {e}")
    
    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down EduMate-AI Backend...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered educational platform for interactive learning",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend dev
        "https://edumate-ai.vercel.app",  # Frontend prod
        "https://*.vercel.app",  # Vercel previews
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
        "*.vercel.app",
        "*.amazonaws.com",
        "*.elasticbeanstalk.com",
    ]
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "Something went wrong"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "edumate-ai-backend",
        "version": settings.app_version,
        "timestamp": time.time()
    }


# Include API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to EduMate-AI Backend",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
