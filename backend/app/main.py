"""
Smart Finance Agent - FastAPI Backend
Main application entry point
"""
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
# Load .env from backend directory
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.utils.logger import get_logger
from app.api import api_router

logger = get_logger("fastapi_backend")


def _validate_api_key() -> None:
    """Validate that required API keys are configured"""
    from app.infrastructure.config import get_active_provider, get_provider_config

    provider = get_active_provider()
    provider_config = get_provider_config()
    api_key_env = provider_config["api_key_env"]
    api_key = os.getenv(api_key_env, "")

    if not api_key or api_key.startswith("your-"):
        error_msg = (
            f"\n{'='*60}\n"
            f"ERROR: {api_key_env} is not configured!\n\n"
            f"Please set your API key in backend/.env:\n"
            f"  {api_key_env}=your-actual-api-key\n\n"
            f"Active provider: {provider}\n"
            f"Required env var: {api_key_env}\n"
            f"{'='*60}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"API Key validated: {api_key_env} = ***configured***")

    # Validate LLM connectivity
    try:
        from app.infrastructure.llm_client import LLMClient
        llm = LLMClient.get_instance()
        logger.info(f"LLM client initialized: model={llm.config.model}")
    except Exception as e:
        logger.warning(f"LLM client initialization warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Initializing Smart Finance Agent Orchestrator...")

    # Validate API keys before initializing orchestrator
    try:
        _validate_api_key()
    except ValueError as e:
        logger.error(f"API key validation failed: {e}")
        # Still allow startup but log the error
        # The orchestrator will fail when actually called

    from app.core.orchestrator import Orchestrator
    orchestrator = Orchestrator(use_router=True)

    # Store orchestrator in app.state for dependency injection
    app.state.orchestrator = orchestrator

    logger.info("Orchestrator initialized successfully")
    yield
    logger.info("Shutting down Smart Finance Agent...")


# Create FastAPI application
app = FastAPI(
    title="Smart Finance Agent API",
    description="AI-powered financial research and analysis platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router (all routes are defined in api/ modules)
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Smart Finance Agent API", "version": "1.0.0"}


@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"status": "ok", "message": "pong"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
