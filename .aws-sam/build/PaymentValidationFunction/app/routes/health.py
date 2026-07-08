"""Health check endpoint."""

from fastapi import APIRouter
from app.models.order import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return application health status."""
    return HealthResponse(
        status="healthy",
        service="order-processing-service",
        version="1.2.0",
    )
