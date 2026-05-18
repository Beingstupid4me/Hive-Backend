from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/summary")
def alpha_summary(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return {"alpha": services.alpha.get_header_meta()}


@router.get("/rankings")
def alpha_rankings(
    limit: int = Query(default=120, ge=1, le=500),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return {"alpha": {"rankings": services.alpha.get_rankings(limit=limit)}}


@router.get("/features")
def alpha_features(
    top_n: int = Query(default=12, ge=1, le=50),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return {"alpha": {"feature_importance": services.alpha.get_feature_importance(top_n=top_n)}}


@router.get("/rolling-ic")
def alpha_rolling_ic(
    window_days: int = Query(default=30, ge=5, le=365),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return {"alpha": {"rolling_rank_ic": services.alpha.get_rolling_rank_ic(window_days=window_days)}}


@router.get("/shap/{ticker}")
def alpha_shap_detail(
    ticker: str,
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return {"alpha": {"shap_detail": services.alpha.get_shap_detail(ticker)}}


@router.get("/logs")
def alpha_logs(
    limit: int = Query(default=25, ge=1, le=200),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return {"alpha": {"execution_log": services.alpha.get_execution_log(limit=limit)}}


@router.get("/all")
def alpha_all(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.alpha.get_alpha_payload()
