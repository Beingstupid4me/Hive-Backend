from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_services
from app.schemas.contracts import OptimizerSolveRequest
from app.services.container import ServiceContainer

router = APIRouter()


@router.post("/solve")
def optimizer_solve(
    payload: OptimizerSolveRequest,
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.optimizer.solve(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/current")
def optimizer_current(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.optimizer.get_current()


@router.get("/{job_id}")
def optimizer_job(job_id: str, services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    try:
        return services.optimizer.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
