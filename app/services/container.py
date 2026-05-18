from __future__ import annotations

from app.core.config import Settings
from app.core.state import AppStateStore
from app.providers.factory import build_market_data_provider
from app.repositories.artifacts import ArtifactRepository
from app.repositories.sp500 import Sp500Repository
from app.services.agent_service import AgentService
from app.services.alpha_service import AlphaService
from app.services.backtest_service import BacktestService
from app.services.execution_service import ExecutionService
from app.services.ledger_service import LedgerService
from app.services.landing_service import LandingService
from app.services.macro_service import MacroService
from app.services.marketing_service import MarketingService
from app.services.metrics_service import MetricsService
from app.services.optimizer_service import OptimizerService
from app.services.risk_service import RiskService
from app.services.system_service import SystemService


class ServiceContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = AppStateStore()

        self.sp500_repository = Sp500Repository(
            data_dir=settings.resolved_sp500_data_dir,
            mapping_file=settings.resolved_ticker_mapping_file,
        )
        self.artifacts = ArtifactRepository(model_data_dir=settings.resolved_model_data_dir)
        self.provider = build_market_data_provider(settings, self.sp500_repository)

        self.system = SystemService(settings)
        self.marketing = MarketingService()
        self.landing = LandingService(self.provider, self.artifacts)
        self.macro = MacroService(settings, self.provider, self.artifacts, self.sp500_repository)
        self.alpha = AlphaService(settings, self.artifacts, self.sp500_repository)
        self.risk = RiskService(settings, self.artifacts, self.sp500_repository, self.state)
        self.ledger = LedgerService(self.state)
        self.execution = ExecutionService(settings, self.provider, self.sp500_repository, self.state, self.ledger)
        self.backtest = BacktestService(settings, self.artifacts, self.sp500_repository)
        self.optimizer = OptimizerService(settings, self.sp500_repository, self.alpha, self.state)
        self.agent = AgentService(self.state, self.macro, self.alpha, self.risk)

        self.metrics = MetricsService(
            system=self.system,
            landing=self.landing,
            marketing=self.marketing,
            macro=self.macro,
            alpha=self.alpha,
            risk=self.risk,
            agent=self.agent,
            backtest=self.backtest,
            execution=self.execution,
            optimizer=self.optimizer,
        )
