"""
Smart Finance Agent - FastAPI Backend
Main application entry point
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add the backend directory to Python path for imports
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(Path(__file__).parent.parent / ".env")

import sentry_sdk
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import api_router
from app.core.startup_check import check_jwt_secret
from app.utils.logger import get_logger

# Monitoring (optional - requires prometheus_client)
try:
    from app.monitoring.middleware import PrometheusMiddleware
    from app.monitoring.routes import metrics_endpoint

    MONITORING_ENABLED = True
except ImportError:
    MONITORING_ENABLED = False

logger = get_logger("fastapi_backend")

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


def init_sentry():
    """Initialize Sentry SDK for error monitoring"""
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")

    if not sentry_dsn:
        logger.warning("SENTRY_DSN not configured. Sentry monitoring disabled.")
        return

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR,
    )

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        integrations=[
            FastApiIntegration(),
            AsyncioIntegration(),
            sentry_logging,
        ],
        traces_sample_rate=0.1 if environment == "production" else 1.0,
        profiles_sample_rate=0.1 if environment == "production" else 0,
        before_send=_before_send,
        attach_stacktrace=True,
        send_default_pii=False,
    )

    logger.info(f"Sentry initialized for environment: {environment}")


def _before_send(event, hint):
    """Filter sensitive data before sending to Sentry"""
    if event.get("request", {}).get("headers"):
        headers = event["request"]["headers"]
        for key in ["authorization", "cookie", "x-api-key"]:
            if key in headers:
                headers[key] = "[FILTERED]"

    if event.get("extra", {}).get("password"):
        event["extra"]["password"] = "[FILTERED]"

    return event


def _validate_api_key() -> None:
    """Validate that required API keys are configured"""
    from app.infrastructure.config import get_active_provider, get_provider_config

    provider = get_active_provider()
    provider_config = get_provider_config()
    api_key_env = provider_config["api_key_env"]
    api_key = os.getenv(api_key_env, "")

    if not api_key or api_key.startswith("your-"):
        error_msg = (
            f"\n{'=' * 60}\n"
            f"ERROR: {api_key_env} is not configured!\n\n"
            f"Please set your API key in backend/.env:\n"
            f"  {api_key_env}=your-actual-api-key\n\n"
            f"Active provider: {provider}\n"
            f"Required env var: {api_key_env}\n"
            f"{'=' * 60}"
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

    # Fail fast if the JWT secret is missing/weak
    check_jwt_secret()

    # Initialize Sentry
    init_sentry()

    # Validate API keys before initializing orchestrator
    try:
        _validate_api_key()
    except ValueError as e:
        logger.error(f"API key validation failed: {e}")
        sentry_sdk.capture_exception(e)

    # Activate profiling integration
    try:
        from app.core.profiling.integration import activate_profiling

        activate_profiling()
        logger.info("Profiling integration activated")
    except Exception as e:
        logger.warning(f"Failed to activate profiling: {e}")

    # Activate dashboard integration
    try:
        from app.core.dashboard_integration import activate_dashboard

        activate_dashboard()
        logger.info("Dashboard integration activated")
    except Exception as e:
        logger.warning(f"Failed to activate dashboard: {e}")

    # Set application info for Prometheus
    if MONITORING_ENABLED:
        try:
            from app.monitoring.prometheus import app_info

            app_info.info(
                {
                    "version": "1.0.0",
                    "environment": os.getenv("ENVIRONMENT", "development"),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to init Prometheus metrics: {e}")

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


# Add rate limiting
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


# Add CORS middleware for frontend communication
_cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept-Language"],
)

# Add Prometheus metrics middleware
if MONITORING_ENABLED:
    try:
        app.add_middleware(PrometheusMiddleware)
    except Exception as e:
        logger.warning(f"Failed to add Prometheus middleware: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler that reports to Sentry"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc)
            if os.getenv("ENVIRONMENT") == "development"
            else "An unexpected error occurred",
        },
    )


@app.middleware("http")
async def sentry_middleware(request: Request, call_next):
    """Middleware to add request context to Sentry"""
    sentry_sdk.set_context(
        "request",
        {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
        },
    )

    response = await call_next(request)

    sentry_sdk.set_tag("http.status_code", response.status_code)

    return response


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


# Prometheus metrics endpoint
if MONITORING_ENABLED:
    try:
        app.add_route("/metrics", metrics_endpoint)
    except Exception as e:
        logger.warning(f"Failed to add metrics endpoint: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
