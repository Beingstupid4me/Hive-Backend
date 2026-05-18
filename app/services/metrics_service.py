from __future__ import annotations

from app.services.agent_service import AgentService
from app.services.alpha_service import AlphaService
from app.services.backtest_service import BacktestService
from app.services.execution_service import ExecutionService
from app.services.landing_service import LandingService
from app.services.macro_service import MacroService
from app.services.marketing_service import MarketingService
from app.services.optimizer_service import OptimizerService
from app.services.risk_service import RiskService
from app.services.system_service import SystemService


class MetricsService:
    def __init__(
        self,
        system: SystemService,
        landing: LandingService,
        marketing: MarketingService,
        macro: MacroService,
        alpha: AlphaService,
        risk: RiskService,
        agent: AgentService,
        backtest: BacktestService,
        execution: ExecutionService,
        optimizer: OptimizerService,
    ) -> None:
        self.system = system
        self.landing = landing
        self.marketing = marketing
        self.macro = macro
        self.alpha = alpha
        self.risk = risk
        self.agent = agent
        self.backtest = backtest
        self.execution = execution
        self.optimizer = optimizer

    def _deep_merge(self, base: dict[str, object], incoming: dict[str, object]) -> dict[str, object]:
        for key, value in incoming.items():
            current = base.get(key)
            if isinstance(current, dict) and isinstance(value, dict):
                self._deep_merge(current, value)
            else:
                base[key] = value
        return base

    async def get_snapshot(self) -> dict[str, object]:
        snapshot: dict[str, object] = {}
        chunks: list[dict[str, object]] = [
            self.system.get_shell_metrics(),
            await self.landing.get_overview(),
            self.marketing.get_about_page(),
            self.marketing.get_methodology_page(),
            self.marketing.get_contact_meta(),
            self.marketing.get_execute_page(),
            await self.macro.get_macro_payload(),
            self.alpha.get_alpha_payload(),
            self.risk.get_risk_payload(),
            await self.agent.get_agent_payload(),
            self.backtest.get_backtest_payload(run_id="latest"),
            await self.execution.get_execution_payload(ticker="AAPL", timeframe="1d"),
            self.optimizer.get_current(),
        ]

        for chunk in chunks:
            self._deep_merge(snapshot, chunk)

        return snapshot
