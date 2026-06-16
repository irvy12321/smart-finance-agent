"""Research Copilot API.

Single product mainline: given a stock symbol, return a trust-annotated
research report (data -> computed indicators -> confidence -> interpretation).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import require_role
from app.auth.models import UserResponse
from app.auth.roles import Role
from app.core.research import ResearchService
from app.utils.logger import get_logger

logger = get_logger("api.research")

router = APIRouter(prefix="/research", tags=["research"])


def _language_from_request(request: Request) -> str:
    accept = request.headers.get("accept-language", "en")
    return "zh" if accept.startswith("zh") else "en"


@router.post("/{symbol}")
async def research_symbol(
    symbol: str,
    request: Request,
    current_user: UserResponse = Depends(require_role(Role.ADMIN, Role.ANALYST)),
) -> dict[str, Any]:
    """Run the research mainline for a single stock symbol (Admin/Analyst)."""
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or len(symbol) > 10:
        raise HTTPException(status_code=400, detail="Invalid stock symbol")

    language = _language_from_request(request)
    try:
        service = ResearchService()
        result = await service.research(symbol, language=language)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Research failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Research failed: {e}") from e
