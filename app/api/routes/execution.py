from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_services
from app.schemas.contracts import AumRequest, OrderRequest
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/book")
async def execution_book(
    ticker: str = Query(default="AAPL"),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return await services.execution.get_order_book(ticker=ticker)


@router.get("/candles")
async def execution_candles(
    ticker: str = Query(default="AAPL"),
    timeframe: str = Query(default="1d"),
    limit: int = Query(default=60, ge=1, le=1000),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return await services.execution.get_candles(ticker=ticker, timeframe=timeframe, limit=limit)


@router.get("/positions")
async def execution_positions(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return await services.execution.get_positions()


@router.get("/orders")
def execution_orders(
    limit: int = Query(default=200, ge=1, le=1000),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return services.execution.get_orders(limit=limit)


@router.post("/order")
async def execution_order(
    payload: OrderRequest,
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return await services.execution.place_order(payload)


@router.get("/ledger")
def execution_ledger(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.execution.get_ledger_payload()


@router.get("/capacity")
async def execution_capacity(
    aum_usd: float = Query(default=100_000.0, ge=10_000.0, le=100_000_000.0),
    ticker: str = Query(default="AAPL"),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return await services.execution.get_friction_projection(aum_usd=aum_usd, ticker=ticker)


@router.post("/capacity")
async def execution_capacity_post(
    payload: AumRequest,
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return await services.execution.get_friction_projection(aum_usd=payload.aum_usd, ticker=payload.ticker)


@router.get("/all")
async def execution_all(
    ticker: str = Query(default="AAPL"),
    timeframe: str = Query(default="1d"),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return await services.execution.get_execution_payload(ticker=ticker, timeframe=timeframe)
