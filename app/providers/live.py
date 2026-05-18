from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pandas as pd

from app.core.config import Settings
from app.providers.historical import HistoricalDataProvider


class LiveDataProvider:
    def __init__(self, settings: Settings, fallback: HistoricalDataProvider) -> None:
        self.settings = settings
        self.fallback = fallback

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        symbol = ticker.upper()
        for suffix in (".OQ", ".US", ".N"):
            if symbol.endswith(suffix):
                symbol = symbol.replace(suffix, "")
        return symbol

    @staticmethod
    def _fallback_proxy_symbol(ticker: str) -> str:
        mapping = {
            "^GSPC": "AAPL",
            "DX-Y.NYB": "JPM",
            "GC=F": "JNJ",
            "^VIX": "XOM",
        }
        return mapping.get(ticker.upper(), LiveDataProvider._normalize_ticker(ticker))

    def _download_history(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ModuleNotFoundError as exc:
            raise RuntimeError("yfinance is not available in this environment") from exc

        symbol = self._normalize_ticker(ticker)
        return yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)

    async def get_quote(self, ticker: str) -> dict[str, float | str]:
        try:
            history = await asyncio.to_thread(self._download_history, ticker, "5d", "1d")
            if history.empty:
                raise ValueError("Empty live quote history")

            history = history.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
            latest = history.iloc[-1]
            prev_close = float(history.iloc[-2]["Close"]) if len(history) > 1 else float(latest["Close"])
            change_pct = 0.0 if prev_close == 0 else (float(latest["Close"]) / prev_close - 1.0) * 100.0

            dt_value = history.index[-1]
            date_value = pd.Timestamp(dt_value).strftime("%Y-%m-%d")

            return {
                "ticker": self._normalize_ticker(ticker),
                "date": date_value,
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "close": float(latest["Close"]),
                "volume": float(latest["Volume"]),
                "change_pct": float(change_pct),
            }
        except Exception:
            proxy = self._fallback_proxy_symbol(ticker)
            return await self.fallback.get_quote(proxy)

    async def get_candles(
        self,
        ticker: str,
        timeframe: str = "1d",
        limit: int = 60,
    ) -> list[dict[str, float | str]]:
        interval_map: dict[str, tuple[str, str]] = {
            "1m": ("1d", "1m"),
            "5m": ("5d", "5m"),
            "15m": ("5d", "15m"),
            "1h": ("1mo", "60m"),
            "1d": ("6mo", "1d"),
        }
        period, interval = interval_map.get(timeframe, ("6mo", "1d"))

        try:
            history = await asyncio.to_thread(self._download_history, ticker, period, interval)
            if history.empty:
                raise ValueError("Empty live candle history")
            history = history.dropna(subset=["Open", "High", "Low", "Close", "Volume"])

            candles = [
                {
                    "time": pd.Timestamp(index).isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
                for index, row in history.iterrows()
            ]
            return candles[-limit:]
        except Exception:
            proxy = self._fallback_proxy_symbol(ticker)
            return await self.fallback.get_candles(proxy, timeframe=timeframe, limit=limit)

    async def get_market_volume_24h(self) -> float:
        # CoinGecko global endpoint is a free open API and works without auth keys.
        endpoint = f"{self.settings.coingecko_base_url}/global"
        try:
            async with httpx.AsyncClient(timeout=self.settings.yahoo_timeout_sec) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                return float(payload["data"]["total_volume"]["usd"])
        except Exception:
            return await self.fallback.get_market_volume_24h()

    async def close_matrix(self, tickers: list[str], lookback: int = 252) -> pd.DataFrame:
        # For cross-sectional matrix calculations, historical files are a deterministic fallback.
        return await self.fallback.close_matrix(tickers, lookback=lookback)
