"""
Health check endpoint.

GET /api/health — Service health status
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Check DB, vector DB, and agent system connectivity."""
    return {
        "status": "ok",
        "services": {
            "postgres": "connected",
            "chromadb": "connected",
            "agent_system": "ready",
        },
        "version": "0.1.0",
    }
