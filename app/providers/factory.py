from __future__ import annotations

from app.core.config import Settings
from app.providers.base import MarketDataProvider
from app.providers.historical import HistoricalDataProvider
from app.providers.live import LiveDataProvider
from app.repositories.sp500 import Sp500Repository


def build_market_data_provider(settings: Settings, sp500_repository: Sp500Repository) -> MarketDataProvider:
    historical_provider = HistoricalDataProvider(sp500_repository)
    if settings.historical_data:
        return historical_provider
    return LiveDataProvider(settings=settings, fallback=historical_provider)
