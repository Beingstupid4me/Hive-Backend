from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/snapshot")
async def metrics_snapshot(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return await services.metrics.get_snapshot()
