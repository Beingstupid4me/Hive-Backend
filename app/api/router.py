from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    agent,
    alpha,
    backtest,
    execution,
    health,
    landing,
    macro,
    marketing,
    metrics,
    optimizer,
    risk,
    system,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(landing.router, prefix="/landing", tags=["landing"])
api_router.include_router(marketing.router, prefix="", tags=["public"])
api_router.include_router(macro.router, prefix="/macro", tags=["macro"])
api_router.include_router(alpha.router, prefix="/alpha", tags=["alpha"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(execution.router, prefix="/execution", tags=["execution"])
api_router.include_router(optimizer.router, prefix="/optimizer", tags=["optimizer"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
