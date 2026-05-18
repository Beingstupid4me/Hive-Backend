from __future__ import annotations

from app.providers.base import MarketDataProvider
from app.repositories.artifacts import ArtifactRepository


class LandingService:
    def __init__(self, provider: MarketDataProvider, artifacts: ArtifactRepository) -> None:
        self.provider = provider
        self.artifacts = artifacts

    def _signal_confidence_score(self) -> float:
        registry = self.artifacts.final_model_registry()
        diagnostics = registry.get("alpha_diagnostics", {})
        mean_rank_ic = float(diagnostics.get("mean_rank_ic", 0.015))
        raw = (mean_rank_ic / 0.02) * 100.0
        return round(max(0.0, min(99.0, raw)), 1)

    def _guardrail_status(self) -> str:
        registry = self.artifacts.final_model_registry()
        oos = registry.get("oos_performance", {})
        max_dd = float(oos.get("max_drawdown_pct", -25.0))
        return "ACTIVE" if max_dd > -30.0 else "WATCH"

    async def get_overview(self) -> dict[str, object]:
        aggregate_volume = await self.provider.get_market_volume_24h()

        tape_symbols = [
            ("US Large Cap", "AAPL"),
            ("US Growth", "MSFT"),
            ("US Energy", "XOM"),
            ("US Defensives", "JNJ"),
        ]

        signal_tape: list[dict[str, object]] = []
        for region, ticker in tape_symbols:
            quote = await self.provider.get_quote(ticker)
            change_pct = float(quote.get("change_pct", 0.0))
            signal_tape.append(
                {
                    "region": region,
                    "value": round(change_pct, 2),
                    "status": "UP" if change_pct >= 0 else "DOWN",
                }
            )

        registry = self.artifacts.final_model_registry()

        return {
            "platform": {
                "protocol_version": registry.get("version", "v2.0.0"),
                "hero": {
                    "headline": "Precision Execution for Sovereign Capital.",
                    "subcopy": "Institutional-grade alpha generation with transparent risk controls.",
                },
                "desks": [
                    {
                        "name": "Macro Regime",
                        "summary": "HMM/GMM state tracking with transition diagnostics.",
                        "href": "/terminal/macro-desk",
                        "status": "ACTIVE",
                    },
                    {
                        "name": "Alpha Factory",
                        "summary": "Cross-sectional ranking, SHAP diagnostics, and decile analytics.",
                        "href": "/terminal/alpha-factory",
                        "status": "ACTIVE",
                    },
                    {
                        "name": "Risk Portfolio",
                        "summary": "HRP allocation, exposure budgets, and active risk controls.",
                        "href": "/terminal/risk-desk",
                        "status": "ACTIVE",
                    },
                    {
                        "name": "Fin-OSS Agent",
                        "summary": "Model-to-human translation layer for daily institutional briefings.",
                        "href": "/terminal/agent",
                        "status": "ACTIVE",
                    },
                ],
                "onboarding": {
                    "headline": "Engage the Institutional Onboarding Desk",
                    "cta_primary_href": "/contact",
                    "cta_secondary_href": "/about",
                },
            },
            "market": {
                "aggregate_volume_24h": round(aggregate_volume, 2),
                "signal_tape": signal_tape,
            },
            "execution": {
                "avg_latency_ms": 0.038,
            },
            "alpha": {
                "signal_confidence_score": self._signal_confidence_score(),
            },
            "infrastructure": {
                "global_nodes_online": 1024,
            },
            "methodology": {
                "stages": [
                    "Data Foundation",
                    "Feature Factory",
                    "Meta-Labeling & Ensemble Alpha",
                    "HRP Portfolio & Agentic Briefing",
                ]
            },
            "risk": {
                "guardrail_status": self._guardrail_status(),
            },
        }
