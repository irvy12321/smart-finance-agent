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

from app.core.orchestrator import Orchestrator
from app.utils.logger import get_logger
from app.api import api_router

logger = get_logger("fastapi_backend")

# Global orchestrator instance (shared with api modules)
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global orchestrator
    logger.info("Initializing Smart Finance Agent Orchestrator...")
    orchestrator = Orchestrator(use_router=True)
    
    # Share orchestrator with api modules
    from app.api import task as task_module
    from app.api import chat as chat_module
    task_module.orchestrator = orchestrator
    chat_module.orchestrator = orchestrator
    
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
