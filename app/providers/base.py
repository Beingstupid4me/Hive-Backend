from __future__ import annotations

from typing import Protocol


class MarketDataProvider(Protocol):
    async def get_quote(self, ticker: str) -> dict[str, float | str]:
        ...

    async def get_candles(
        self,
        ticker: str,
        timeframe: str = "1d",
        limit: int = 60,
    ) -> list[dict[str, float | str]]:
        ...

    async def get_market_volume_24h(self) -> float:
        ...
