from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/summary")
def risk_summary(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.risk.get_summary()


@router.get("/clusters")
def risk_clusters(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return {"risk": {"clusters": services.risk.get_clusters()}}


@router.get("/dendrogram")
def risk_dendrogram(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return {"risk": {"dendrogram": services.risk.get_dendrogram()}}


@router.get("/orders")
def risk_orders(
    limit: int = Query(default=50, ge=1, le=500),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return {"risk": {"active_orders": services.risk.get_active_orders(limit=limit)}}


@router.get("/all")
def risk_all(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.risk.get_risk_payload()
