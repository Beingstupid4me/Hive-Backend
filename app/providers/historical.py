from __future__ import annotations

from typing import Sequence

import pandas as pd

from app.repositories.sp500 import Sp500Repository


class HistoricalDataProvider:
    def __init__(self, sp500_repository: Sp500Repository) -> None:
        self.sp500_repository = sp500_repository

    async def get_quote(self, ticker: str) -> dict[str, float | str]:
        return self.sp500_repository.latest_bar(ticker)

    async def get_candles(
        self,
        ticker: str,
        timeframe: str = "1d",
        limit: int = 60,
    ) -> list[dict[str, float | str]]:
        # Historical storage is daily OHLCV, so lower timeframes are downsampled from daily bars.
        _ = timeframe
        history = self.sp500_repository.get_history(ticker, lookback=max(limit, 2))
        if history.empty:
            return []

        return [
            {
                "time": row.Date.strftime("%Y-%m-%d"),
                "open": float(row.Open),
                "high": float(row.High),
                "low": float(row.Low),
                "close": float(row.Close),
                "volume": float(row.Volume),
            }
            for row in history.itertuples(index=False)
        ][-limit:]

    async def get_market_volume_24h(self) -> float:
        tickers: Sequence[str] = self.sp500_repository.list_tickers(limit=80)
        total = 0.0
        for ticker in tickers:
            try:
                latest = self.sp500_repository.latest_bar(ticker)
            except (ValueError, FileNotFoundError):
                continue
            total += float(latest["close"]) * float(latest["volume"])
        return total

    async def close_matrix(self, tickers: list[str], lookback: int = 252) -> pd.DataFrame:
        return self.sp500_repository.close_matrix(tickers, lookback=lookback)
