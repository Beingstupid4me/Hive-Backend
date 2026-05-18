from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/overview")
async def landing_overview(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return await services.landing.get_overview()
