from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


class Sp500Repository:
    def __init__(self, data_dir: Path, mapping_file: Path) -> None:
        self.data_dir = data_dir
        self.mapping_file = mapping_file
        self._history_cache: dict[str, pd.DataFrame] = {}
        self._company_map = self._load_company_map()

    def _load_company_map(self) -> dict[str, str]:
        if not self.mapping_file.exists():
            return {}
        mapping_df = pd.read_csv(self.mapping_file)
        if {"Ticker", "Company_Name"}.issubset(mapping_df.columns):
            return {
                str(row["Ticker"]).upper(): str(row["Company_Name"])
                for _, row in mapping_df.iterrows()
            }
        return {}

    def list_tickers(self, limit: int | None = None) -> list[str]:
        tickers = sorted(path.stem.upper() for path in self.data_dir.glob("*.csv"))
        return tickers if limit is None else tickers[:limit]

    def get_company_name(self, ticker: str) -> str:
        symbol = ticker.upper()
        return self._company_map.get(symbol, symbol)

    def _read_history(self, ticker: str) -> pd.DataFrame:
        symbol = ticker.upper()
        if symbol in self._history_cache:
            return self._history_cache[symbol].copy()

        path = self.data_dir / f"{symbol}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Ticker file not found: {symbol}")

        df = pd.read_csv(path, parse_dates=["Date"])
        required = {"Date", "Open", "High", "Low", "Close", "Volume"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Ticker {symbol} missing required columns: {sorted(missing)}")

        df = df.sort_values("Date").reset_index(drop=True)
        self._history_cache[symbol] = df
        return df.copy()

    def get_history(
        self,
        ticker: str,
        lookback: int | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        df = self._read_history(ticker)

        if start is not None:
            df = df[df["Date"] >= pd.to_datetime(start)]
        if end is not None:
            df = df[df["Date"] <= pd.to_datetime(end)]
        if lookback is not None and lookback > 0:
            df = df.tail(lookback)

        return df.reset_index(drop=True)

    def latest_bar(self, ticker: str) -> dict[str, float | str]:
        df = self.get_history(ticker, lookback=2)
        if df.empty:
            raise ValueError(f"No history available for {ticker}")

        latest = df.iloc[-1]
        prev_close = float(df.iloc[-2]["Close"]) if len(df) > 1 else float(latest["Close"])
        change_pct = 0.0 if prev_close == 0 else (float(latest["Close"]) / prev_close - 1.0) * 100.0

        return {
            "ticker": ticker.upper(),
            "date": latest["Date"].strftime("%Y-%m-%d"),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": float(latest["Volume"]),
            "change_pct": float(change_pct),
        }

    def close_matrix(self, tickers: Iterable[str], lookback: int = 252) -> pd.DataFrame:
        series_map: dict[str, pd.Series] = {}
        for ticker in tickers:
            try:
                hist = self.get_history(ticker, lookback=lookback + 5)
            except (FileNotFoundError, ValueError):
                continue
            if hist.empty:
                continue
            series_map[ticker.upper()] = hist.set_index("Date")["Close"]

        if not series_map:
            return pd.DataFrame()

        matrix = pd.concat(series_map, axis=1).dropna(how="any")
        if len(matrix) > lookback:
            matrix = matrix.tail(lookback)
        return matrix
