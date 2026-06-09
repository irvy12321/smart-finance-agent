"""
API routes package
"""
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.task import router as task_router
from app.api.report import router as report_router
from app.api.system import router as system_router
from app.api.tools import router as tools_router
from app.api.chat import router as chat_router
from app.api.rag import router as rag_router

# Create main API router (NO prefix here - will be added in main.py)
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router)
api_router.include_router(task_router)
api_router.include_router(report_router)
api_router.include_router(system_router)
api_router.include_router(tools_router)
api_router.include_router(chat_router)
api_router.include_router(rag_router)


@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Smart Finance Agent API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "task": "/api/task",
            "report": "/api/report",
            "system": "/api/system",
            "tools": "/api/tools",
            "chat": "/api/chat",
            "rag": "/api/rag",
        }
    }
