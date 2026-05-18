from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/{run_id}")
def backtest_run(run_id: str, services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.backtest.get_backtest_payload(run_id=run_id)
