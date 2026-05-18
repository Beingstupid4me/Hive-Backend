from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.config import Settings
from app.providers.base import MarketDataProvider
from app.repositories.artifacts import ArtifactRepository
from app.repositories.sp500 import Sp500Repository


class MacroService:
    REGIME_LABELS = {0: "LOW_VOL_BULL", 1: "TRANSITION", 2: "HIGH_VOL_BEAR"}
    DISPLAY_LABELS = {
        "LOW_VOL_BULL": "Bull",
        "TRANSITION": "Transition",
        "HIGH_VOL_BEAR": "Bear",
        "SIDEWAYS": "Sideways",
    }

    def __init__(
        self,
        settings: Settings,
        provider: MarketDataProvider,
        artifacts: ArtifactRepository,
        sp500_repository: Sp500Repository,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.artifacts = artifacts
        self.sp500_repository = sp500_repository

    def _weights(self) -> pd.DataFrame:
        weights = self.artifacts.weights_log()
        if weights.empty:
            return pd.DataFrame(columns=["date", "regime", "n_stocks", "leverage", "turnover"])
        cols = [c for c in ["date", "regime", "n_stocks", "leverage", "turnover"] if c in weights.columns]
        return weights[cols].dropna(subset=["date", "regime"]).sort_values("date").reset_index(drop=True)

    def _transition_matrix(self) -> dict[str, dict[str, float]]:
        weights = self._weights()
        labels = ["LOW_VOL_BULL", "TRANSITION", "HIGH_VOL_BEAR", "SIDEWAYS"]
        counts = {a: {b: 0 for b in labels} for a in labels}

        if len(weights) < 2:
            return {a: {b: 0.0 for b in labels} for a in labels}

        regimes = weights["regime"].astype(int).tolist()
        for prev_regime, next_regime in zip(regimes[:-1], regimes[1:]):
            a = self.REGIME_LABELS.get(prev_regime, "TRANSITION")
            b = self.REGIME_LABELS.get(next_regime, "TRANSITION")
            counts[a][b] += 1

        probs: dict[str, dict[str, float]] = {}
        for from_state, row in counts.items():
            total = sum(row.values())
            if total == 0:
                probs[from_state] = {to_state: 0.0 for to_state in labels}
            else:
                probs[from_state] = {to_state: row[to_state] / total for to_state in labels}
        return probs

    def _historical_volatility_proxy(self) -> tuple[float, float]:
        matrix = self.sp500_repository.close_matrix(["AAPL", "MSFT", "JPM", "XOM", "JNJ"], lookback=90)
        if matrix.empty or len(matrix) < 50:
            return 14.0, -1.5

        market_returns = matrix.pct_change().dropna().mean(axis=1)
        current = float(market_returns.tail(21).std(ddof=0) * np.sqrt(252) * 100.0)
        prev_window = market_returns.iloc[-42:-21]
        previous = float(prev_window.std(ddof=0) * np.sqrt(252) * 100.0) if len(prev_window) > 5 else current
        delta = 0.0 if previous == 0 else ((current - previous) / previous) * 100.0
        return current, delta

    def _current_regime_info(self) -> tuple[str, float, float, float]:
        weights = self._weights()
        if weights.empty:
            return "TRANSITION", 0.5, 80.0, 0.0

        latest = weights.iloc[-1]
        previous = weights.iloc[-2] if len(weights) > 1 else latest

        regime_label = self.REGIME_LABELS.get(int(latest["regime"]), "TRANSITION")
        matrix = self._transition_matrix()
        row_probs = matrix.get(regime_label, {})
        confidence = max(row_probs.values()) if row_probs else 0.5

        latest_liquidity = 65.0 + float(latest.get("n_stocks", 25)) * 0.7 - float(latest.get("turnover", 1.2)) * 8.0
        prev_liquidity = 65.0 + float(previous.get("n_stocks", 25)) * 0.7 - float(previous.get("turnover", 1.2)) * 8.0
        latest_liquidity = max(0.0, min(100.0, latest_liquidity))
        prev_liquidity = max(0.0, min(100.0, prev_liquidity))
        liquidity_delta = 0.0 if prev_liquidity == 0 else ((latest_liquidity - prev_liquidity) / prev_liquidity) * 100.0

        return regime_label, confidence, latest_liquidity, liquidity_delta

    async def get_summary(self) -> dict[str, object]:
        regime_label, confidence, liquidity_score, liquidity_delta = self._current_regime_info()
        transition_matrix = self._transition_matrix()

        vol_index, vol_change = self._historical_volatility_proxy()
        if not self.settings.historical_data:
            try:
                vix_quote = await self.provider.get_quote("^VIX")
                vol_index = float(vix_quote.get("close", vol_index))
                vol_change = float(vix_quote.get("change_pct", vol_change))
            except Exception:
                pass

        correlation_skew = float(np.clip((vol_index - 12.0) / 100.0, -1.0, 1.0))
        current_row = transition_matrix.get(
            regime_label,
            {
                "LOW_VOL_BULL": 0.33,
                "TRANSITION": 0.34,
                "HIGH_VOL_BEAR": 0.33,
                "SIDEWAYS": 0.0,
            },
        )

        return {
            "regime": {
                "current_state": regime_label,
                "confidence": round(confidence, 4),
                "state_probabilities": {
                    "LOW_VOL_BULL": round(float(current_row.get("LOW_VOL_BULL", 0.0)), 4),
                    "TRANSITION": round(float(current_row.get("TRANSITION", 0.0)), 4),
                    "HIGH_VOL_BEAR": round(float(current_row.get("HIGH_VOL_BEAR", 0.0)), 4),
                    "SIDEWAYS": round(float(current_row.get("SIDEWAYS", 0.0)), 4),
                },
                "weather_label": self.DISPLAY_LABELS.get(regime_label, regime_label),
                "transition_matrix": {
                    from_state: {
                        to_state: round(float(prob), 4)
                        for to_state, prob in to_probs.items()
                    }
                    for from_state, to_probs in transition_matrix.items()
                },
            },
            "macro": {
                "volatility_index": round(vol_index, 2),
                "volatility_change_pct": round(vol_change, 2),
                "liquidity_score": round(liquidity_score, 2),
                "liquidity_change_pct": round(liquidity_delta, 2),
                "correlation_skew": round(correlation_skew, 4),
            },
        }

    def get_history(self, limit: int = 90) -> list[dict[str, object]]:
        weights = self._weights().tail(limit).reset_index(drop=True)
        if weights.empty:
            return []

        regimes = weights["regime"].astype(int)
        price = 4200.0
        rows: list[dict[str, object]] = []
        for i, row in weights.iterrows():
            regime_id = int(row["regime"])
            drift = {0: 0.0012, 1: 0.0003, 2: -0.0010}.get(regime_id, 0.0002)
            seasonal = np.sin(i / 5.0) * 0.0008
            price *= 1.0 + drift + seasonal

            window = regimes.iloc[max(0, i - 20) : i + 1]
            bull_prob = float((window == 0).mean())
            transition_prob = float((window == 1).mean())
            bear_prob = float((window == 2).mean())

            rows.append(
                {
                    "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                    "bull_prob": round(bull_prob, 4),
                    "bear_prob": round(bear_prob, 4),
                    "neutral_prob": round(transition_prob, 4),
                    "price": round(price, 2),
                }
            )

        return rows

    def get_latent_factors(self) -> list[dict[str, object]]:
        regime_meta = self.artifacts.regime_meta()
        state_vol_map = regime_meta.get("state_vol_mapping", {})
        vols = [float(v) for v in state_vol_map.values()] if state_vol_map else [0.15, 0.09, 0.3]
        return [
            {"name": "Greek Skew", "value": round(float(np.mean(vols)) * 10.0, 3)},
            {"name": "Gamma Stress", "value": round(float(np.max(vols)) * 8.0, 3)},
            {"name": "Tail Risk", "value": round(float(np.std(vols)) * 20.0, 3)},
            {"name": "Carry", "value": round(float(np.min(vols)) * 12.0, 3)},
        ]

    async def get_cross_asset_context(self) -> list[dict[str, object]]:
        if self.settings.historical_data:
            symbols = [("SPX Proxy", "AAPL"), ("DXY Proxy", "JPM"), ("GOLD Proxy", "JNJ"), ("VIX Proxy", "XOM")]
        else:
            symbols = [("SPX", "^GSPC"), ("DXY", "DX-Y.NYB"), ("GOLD", "GC=F"), ("VIX", "^VIX")]

        rows: list[dict[str, object]] = []
        for asset, ticker in symbols:
            quote = await self.provider.get_quote(ticker)
            rows.append(
                {
                    "asset": asset,
                    "value": round(float(quote.get("change_pct", 0.0)), 3),
                }
            )
        return rows

    def get_transition_events(self, limit: int = 20) -> list[dict[str, object]]:
        weights = self._weights()
        if len(weights) < 2:
            return []

        rows: list[dict[str, object]] = []
        prev_regime = int(weights.iloc[0]["regime"])
        for _, row in weights.iloc[1:].iterrows():
            current_regime = int(row["regime"])
            if current_regime != prev_regime:
                from_state = self.REGIME_LABELS.get(prev_regime, "TRANSITION")
                to_state = self.REGIME_LABELS.get(current_regime, "TRANSITION")
                from_label = self.DISPLAY_LABELS.get(from_state, from_state)
                to_label = self.DISPLAY_LABELS.get(to_state, to_state)
                severity = "high" if (prev_regime == 2 or current_regime == 2) else "medium"
                rows.append(
                    {
                        "ts": pd.Timestamp(row["date"]).isoformat(),
                        "event": f"{from_label} -> {to_label}",
                        "detail": "Regime state transition detected from rolling HMM sequence.",
                        "severity": severity,
                    }
                )
                prev_regime = current_regime

        return list(reversed(rows[-limit:]))

    async def get_macro_payload(self) -> dict[str, object]:
        summary = await self.get_summary()
        return {
            **summary,
            "regime": {
                **summary["regime"],
                "history": self.get_history(limit=90),
                "transition_events": self.get_transition_events(limit=20),
            },
            "macro": {
                **summary["macro"],
                "latent_factors": self.get_latent_factors(),
                "cross_asset_context": await self.get_cross_asset_context(),
            },
        }
