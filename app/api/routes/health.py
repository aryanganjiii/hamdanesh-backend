"""Health and non-secret runtime configuration status."""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "ok": True,
        "ai_enabled": settings.ai_enabled,
        "provider_configured": settings.provider_configured,
        **request.app.state.document_service.stats(),
    }
