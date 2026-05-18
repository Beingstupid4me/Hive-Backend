from __future__ import annotations

from datetime import datetime, timezone

from app.core.state import AppStateStore
from app.services.alpha_service import AlphaService
from app.services.macro_service import MacroService
from app.services.risk_service import RiskService


class AgentService:
    def __init__(
        self,
        state: AppStateStore,
        macro_service: MacroService,
        alpha_service: AlphaService,
        risk_service: RiskService,
    ) -> None:
        self.state = state
        self.macro_service = macro_service
        self.alpha_service = alpha_service
        self.risk_service = risk_service
        self._seed_worker_stream()

    def _seed_worker_stream(self) -> None:
        if self.state.agent_worker_stream:
            return

        ts = datetime.now(timezone.utc).replace(microsecond=0)
        template = [
            ("info", "Loading regime transition matrix."),
            ("info", "Refreshing alpha confidence diagnostics."),
            ("success", "Meta-quant briefing package compiled."),
        ]
        for i, (level, message) in enumerate(template):
            self.state.agent_worker_stream.append(
                {
                    "ts": (ts).isoformat(),
                    "level": level,
                    "message": message,
                    "seq": i + 1,
                }
            )

    async def get_summary(self) -> dict[str, object]:
        macro = await self.macro_service.get_summary()
        alpha = self.alpha_service.get_header_meta()

        regime_state = str(macro["regime"]["current_state"])
        regime_label = str(macro["regime"].get("weather_label", regime_state))
        sigma_change = float(macro["macro"]["volatility_change_pct"])
        alpha_strength = float(alpha["model_confidence_pct"]) / 100.0

        if regime_state == "LOW_VOL_BULL":
            rotation = "Aggressive"
        elif regime_state == "HIGH_VOL_BEAR":
            rotation = "Defensive"
        else:
            rotation = "Balanced"

        risk = self.risk_service.get_summary()
        turnover_proxy = float(risk["risk"].get("total_exposure_change_pct", 0.0))

        return {
            "agent": {
                "regime_label": regime_label,
                "regime_sigma_change_pct": round(sigma_change, 3),
                "alpha_signal_strength": round(alpha_strength, 4),
                "alpha_signal_change_pct": round((alpha_strength - 0.5) * 10.0, 3),
                "rotation_label": rotation,
                "rotation_rate_pct_per_day": round(abs(turnover_proxy) + 6.5, 3),
            }
        }

    async def _daily_brief(self) -> str:
        macro = await self.macro_service.get_summary()
        alpha = self.alpha_service.get_header_meta()
        risk = self.risk_service.get_summary()

        regime = macro["regime"].get("weather_label", macro["regime"]["current_state"])
        confidence = float(macro["regime"]["confidence"]) * 100.0
        model_conf = alpha["model_confidence_pct"]
        exposure = risk["risk"]["total_exposure_usd"]

        return (
            f"### Daily Quantitative Brief\n"
            f"- Regime state: **{regime}** with {confidence:.1f}% transition confidence.\n"
            f"- Alpha model confidence: **{model_conf:.1f}%** with stable feature breadth.\n"
            f"- Portfolio exposure: **${exposure:,.0f}** under active guardrail supervision.\n"
            f"- Recommendation: preserve regime-aware leverage and prioritize top-decile alpha longs with strongest SHAP alignment."
        )

    def _regime_heatmap(self) -> list[dict[str, object]]:
        values: list[dict[str, object]] = []
        for y in range(6):
            for x in range(12):
                intensity = ((x + 1) * (y + 2)) % 10 / 10.0
                if intensity > 0.7:
                    state = "Bull"
                elif intensity < 0.3:
                    state = "Bear"
                else:
                    state = "Transition"
                values.append({"x": x, "y": y, "intensity": round(intensity, 3), "state": state})
        return values

    def get_worker_stream(self, limit: int = 200) -> list[dict[str, object]]:
        return list(self.state.agent_worker_stream)[-limit:]

    @staticmethod
    def stream_tokens(text: str) -> list[str]:
        words = text.split(" ")
        if not words:
            return []
        return [f"{word} " if i < len(words) - 1 else word for i, word in enumerate(words)]

    async def get_daily_brief_text(self) -> str:
        return await self._daily_brief()

    def get_tools(self) -> list[dict[str, object]]:
        return [
            {"tool": "hmm_regime_reader", "enabled": True},
            {"tool": "hrp_weight_audit", "enabled": True},
            {"tool": "alpha_shap_viewer", "enabled": True},
            {"tool": "execution_router", "enabled": True},
            {"tool": "policy_guardrail", "enabled": True},
        ]

    async def answer_query(self, query: str) -> dict[str, object]:
        lower = query.lower()
        if "risk" in lower or "drawdown" in lower:
            recommendation = "Reduce leverage one step and rotate toward low-volatility clusters until transition risk decays."
        elif "alpha" in lower or "signal" in lower:
            recommendation = "Prioritize top-decile names with persistent rank IC support and avoid weak-confidence mid-decile names."
        else:
            recommendation = "Maintain current regime-aware posture and monitor transition probabilities in the next rebalance window."

        response = {
            "query": query,
            "answer": recommendation,
            "suggested_command": "rebalance_portfolio(mode='hrp_meta_kelly', guardrails='strict')",
        }

        self.state.agent_worker_stream.append(
            {
                "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "level": "info",
                "message": f"Processed agent query: {query[:120]}",
            }
        )
        return response

    async def get_agent_payload(self) -> dict[str, object]:
        summary = await self.get_summary()
        return {
            **summary,
            "agent": {
                **summary["agent"],
                "daily_brief_markdown": await self._daily_brief(),
                "suggested_command": "rebalance_portfolio(mode='hrp_meta_kelly', guardrails='strict')",
                "regime_heatmap": self._regime_heatmap(),
                "worker_stream": self.get_worker_stream(limit=200),
                "tools": self.get_tools(),
                "query_input": "",
            },
        }
