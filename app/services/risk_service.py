from __future__ import annotations

import ast
from datetime import datetime, timezone

import numpy as np

from app.core.config import Settings
from app.core.state import AppStateStore
from app.repositories.artifacts import ArtifactRepository
from app.repositories.sp500 import Sp500Repository
from app.utils.time_utils import parse_percent


class RiskService:
    SECTOR_MAP = {
        "AAPL": "TECH",
        "MSFT": "TECH",
        "NVDA": "TECH",
        "AMD": "TECH",
        "META": "COMM",
        "GOOGL": "COMM",
        "GOOG": "COMM",
        "JPM": "FINANCIALS",
        "BAC": "FINANCIALS",
        "GS": "FINANCIALS",
        "XOM": "ENERGY",
        "CVX": "ENERGY",
        "COP": "ENERGY",
        "JNJ": "HEALTHCARE",
        "UNH": "HEALTHCARE",
        "PFE": "HEALTHCARE",
        "WMT": "CONSUMER",
        "COST": "CONSUMER",
        "AMZN": "CONSUMER",
    }

    def __init__(
        self,
        settings: Settings,
        artifacts: ArtifactRepository,
        sp500_repository: Sp500Repository,
        state: AppStateStore,
    ) -> None:
        self.settings = settings
        self.artifacts = artifacts
        self.sp500_repository = sp500_repository
        self.state = state
        self._seed_active_orders()

    def _weights_log(self):
        return self.artifacts.weights_log()

    def _latest_holdings(self) -> list[tuple[str, float]]:
        weights = self._weights_log()
        if weights.empty or "top_holdings" not in weights.columns:
            return []

        text = str(weights.iloc[-1]["top_holdings"])
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return []

        output: list[tuple[str, float]] = []
        for item in parsed:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            ticker = str(item[0]).upper()
            weight = float(item[1])
            if weight > 0:
                output.append((ticker, weight))
        return output

    def _sector_bucket(self, ticker: str) -> str:
        symbol = ticker.upper()
        if symbol in self.SECTOR_MAP:
            return self.SECTOR_MAP[symbol]

        first = symbol[0]
        if first in {"A", "B", "C", "D", "E"}:
            return "INDUSTRIALS"
        if first in {"F", "G", "H", "I", "J", "K"}:
            return "FINANCIALS"
        if first in {"L", "M", "N", "O", "P"}:
            return "TECH"
        if first in {"Q", "R", "S", "T", "U"}:
            return "HEALTHCARE"
        return "CONSUMER"

    def _build_clusters(self) -> list[dict[str, object]]:
        holdings = self._latest_holdings()
        if not holdings:
            return []

        sector_weights: dict[str, float] = {}
        sector_assets: dict[str, list[str]] = {}

        total_weight = sum(weight for _, weight in holdings) or 1.0
        for ticker, weight in holdings:
            sector = self._sector_bucket(ticker)
            sector_weights[sector] = sector_weights.get(sector, 0.0) + (weight / total_weight)
            sector_assets.setdefault(sector, []).append(ticker)

        sectors = sorted(sector_weights.keys())
        risk_proxy = np.array([sector_weights[s] for s in sectors], dtype=float)
        risk_proxy = np.maximum(risk_proxy, 1e-6)
        risk_contrib = risk_proxy / risk_proxy.sum()

        clusters: list[dict[str, object]] = []
        for i, sector in enumerate(sectors, start=1):
            clusters.append(
                {
                    "cluster_id": f"C-{i:02d}",
                    "label": sector,
                    "weight": round(float(sector_weights[sector]), 4),
                    "risk_contribution": round(float(risk_contrib[i - 1]), 4),
                    "assets": sorted(sector_assets[sector])[:8],
                }
            )
        return clusters

    def _seed_active_orders(self) -> None:
        if self.state.risk_active_orders:
            return

        ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        for ticker, side, shares, price in [
            ("NVDA", "BUY", 1200, 784.20),
            ("XOM", "SELL", 900, 112.45),
            ("JNJ", "BUY", 700, 166.10),
        ]:
            self.state.risk_active_orders.append(
                {
                    "ticker": ticker,
                    "side": side,
                    "shares": shares,
                    "price": price,
                    "status": "WORKING",
                    "timestamp": ts,
                }
            )

    def get_summary(self) -> dict[str, object]:
        weights = self._weights_log()
        latest_leverage = 1.0
        previous_leverage = 1.0

        if not weights.empty and "leverage" in weights.columns:
            latest_leverage = float(weights.iloc[-1]["leverage"])
            previous_leverage = float(weights.iloc[-2]["leverage"]) if len(weights) > 1 else latest_leverage

        exposure = self.settings.base_notional_usd * latest_leverage
        exposure_delta = 0.0 if previous_leverage == 0 else ((latest_leverage - previous_leverage) / previous_leverage) * 100.0

        holdings = self._latest_holdings()
        if holdings:
            weights_norm = np.array([w for _, w in holdings], dtype=float)
            weights_norm = weights_norm / weights_norm.sum()
            herfindahl = float(np.sum(weights_norm**2))
            diversification_ratio = float(np.clip(1.0 - herfindahl, 0.0, 1.0))
        else:
            diversification_ratio = 0.5

        portfolio_perf = self.artifacts.portfolio_performance()
        expected_volatility = 14.2
        max_drawdown = -20.0
        if not portfolio_perf.empty:
            row = portfolio_perf[portfolio_perf["Strategy"] == "HRP + Meta + Kelly + Regime"]
            if not row.empty:
                expected_volatility = parse_percent(row.iloc[0]["Annual Vol"])
                max_drawdown = parse_percent(row.iloc[0]["Max Drawdown"])

        clusters = self._build_clusters()
        return {
            "risk": {
                "total_exposure_usd": round(exposure, 2),
                "total_exposure_change_pct": round(exposure_delta, 2),
                "diversification_ratio": round(diversification_ratio, 4),
                "diversification_change": round((diversification_ratio - 0.75), 4),
                "cluster_count": len(clusters),
                "expected_volatility_pct": round(expected_volatility, 2),
                "system_status": "STABLE" if max_drawdown > -30.0 else "DEFENSIVE",
                "guardrail_status": "ACTIVE" if max_drawdown > -30.0 else "WATCH",
            }
        }

    def get_clusters(self) -> list[dict[str, object]]:
        return self._build_clusters()

    def get_active_orders(self, limit: int = 50) -> list[dict[str, object]]:
        rows = list(self.state.risk_active_orders)
        return rows[-limit:]

    def get_dendrogram(self) -> dict[str, object]:
        clusters = self._build_clusters()
        nodes: list[dict[str, object]] = [
            {
                "id": "ROOT",
                "label": "HRP_ROOT",
                "level": 0,
                "weight": 1.0,
            }
        ]
        links: list[dict[str, object]] = []

        for cluster in clusters:
            cluster_id = str(cluster["cluster_id"])
            cluster_weight = float(cluster["weight"])
            nodes.append(
                {
                    "id": cluster_id,
                    "label": str(cluster["label"]),
                    "level": 1,
                    "weight": cluster_weight,
                    "risk_contribution": float(cluster["risk_contribution"]),
                }
            )
            links.append(
                {
                    "source": "ROOT",
                    "target": cluster_id,
                    "distance": round(max(0.05, 1.0 - cluster_weight), 4),
                }
            )

            for asset in cluster["assets"][:8]:
                asset_node = f"{cluster_id}:{asset}"
                local_dist = 0.15 + ((sum(ord(ch) for ch in asset) % 35) / 100.0)
                nodes.append(
                    {
                        "id": asset_node,
                        "label": str(asset),
                        "level": 2,
                        "weight": round(cluster_weight / max(len(cluster["assets"]), 1), 6),
                    }
                )
                links.append(
                    {
                        "source": cluster_id,
                        "target": asset_node,
                        "distance": round(local_dist, 4),
                    }
                )

        return {
            "nodes": nodes,
            "links": links,
            "root": "ROOT",
        }

    def get_risk_payload(self) -> dict[str, object]:
        summary = self.get_summary()
        return {
            **summary,
            "risk": {
                **summary["risk"],
                "clusters": self.get_clusters(),
                "active_orders": self.get_active_orders(),
                "dendrogram": self.get_dendrogram(),
            },
        }
