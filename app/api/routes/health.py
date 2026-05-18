from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/health")
def health(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    settings = services.settings
    return {
        "status": "ok",
        "mode": "historical" if settings.historical_data else "live",
        "sp500_data_dir": str(settings.resolved_sp500_data_dir),
        "model_data_dir": str(settings.resolved_model_data_dir),
    }
