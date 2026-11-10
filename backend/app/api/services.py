from fastapi import APIRouter

from app.schemas.service import ServiceStatusRead
from services.music.aggregator import aggregator

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=list[ServiceStatusRead])
async def list_services() -> list[ServiceStatusRead]:
    """Returns the list of music source services and their online availability status."""
    statuses = aggregator.get_services_status()
    return [ServiceStatusRead(**s) for s in statuses]
