from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiEnvelope(BaseModel):
    mode: Literal["historical", "live"]
    updated_at: str
    data: dict[str, Any]


class ContactRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=240)
    organization: str | None = Field(default=None, max_length=180)
    message: str = Field(min_length=10, max_length=5000)


class AgentQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)


class OrderRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=24)
    side: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    algo: str = Field(default="VWAP", max_length=40)


class AumRequest(BaseModel):
    aum_usd: float = Field(ge=10_000.0, le=100_000_000.0)
    ticker: str = Field(default="AAPL", min_length=1, max_length=24)


class OptimizerSolveRequest(BaseModel):
    target_return_pct: float = Field(default=12.5, ge=0.0, le=100.0)
    volatility_cap_pct: float = Field(default=8.0, ge=0.1, le=100.0)
    max_asset_weight_pct: float = Field(default=15.0, ge=0.1, le=100.0)
    sector_neutrality: bool = True
    tickers: list[str] | None = None
