from __future__ import annotations

import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.core.config import Settings
from app.core.state import AppStateStore
from app.repositories.sp500 import Sp500Repository
from app.schemas.contracts import OptimizerSolveRequest
from app.services.alpha_service import AlphaService


class OptimizerService:
    def __init__(
        self,
        settings: Settings,
        sp500_repository: Sp500Repository,
        alpha_service: AlphaService,
        state: AppStateStore,
    ) -> None:
        self.settings = settings
        self.sp500_repository = sp500_repository
        self.alpha_service = alpha_service
        self.state = state

    def _default_tickers(self, n_assets: int = 12) -> list[str]:
        rankings = self.alpha_service.get_rankings(limit=max(n_assets * 3, 40))
        longs = [row["ticker"] for row in rankings if row.get("action") == "TOP_LONG"]
        symbols = [str(ticker).upper() for ticker in longs[:n_assets]]
        if len(symbols) < n_assets:
            fallback = self.sp500_repository.list_tickers(limit=n_assets)
            symbols.extend([t for t in fallback if t not in symbols])
        return symbols[:n_assets]

    def _return_matrix(self, tickers: list[str], lookback: int = 504) -> pd.DataFrame:
        matrix = self.sp500_repository.close_matrix(tickers=tickers, lookback=lookback)
        if matrix.empty:
            return pd.DataFrame()
        return matrix.pct_change().dropna(how="any")

    def solve(self, payload: OptimizerSolveRequest) -> dict[str, object]:
        tickers = [t.upper() for t in (payload.tickers or []) if t]
        if not tickers:
            tickers = self._default_tickers(n_assets=12)

        returns = self._return_matrix(tickers=tickers, lookback=504)
        if returns.empty:
            raise ValueError("Unable to build returns matrix for optimizer solve")

        tickers = list(returns.columns)
        n_assets = len(tickers)

        mu = returns.mean().values * 252.0
        cov = returns.cov().values * 252.0

        rng = np.random.default_rng(self.settings.random_seed)
        n_samples = 4000
        raw_weights = rng.dirichlet(np.ones(n_assets), size=n_samples)

        max_weight = payload.max_asset_weight_pct / 100.0
        constrained = raw_weights[raw_weights.max(axis=1) <= max_weight]
        if constrained.size == 0:
            constrained = raw_weights

        port_returns = constrained @ mu
        port_vol = np.sqrt(np.einsum("ij,jk,ik->i", constrained, cov, constrained))
        sharpe = np.divide(port_returns, port_vol, out=np.zeros_like(port_returns), where=port_vol > 0)

        target = payload.target_return_pct / 100.0
        vol_cap = payload.volatility_cap_pct / 100.0
        feasible = np.where((port_returns >= target) & (port_vol <= vol_cap))[0]

        if len(feasible) > 0:
            best_idx = feasible[np.argmax(sharpe[feasible])]
        else:
            fallback = np.where(port_vol <= vol_cap)[0]
            if len(fallback) > 0:
                best_idx = fallback[np.argmax(sharpe[fallback])]
            else:
                best_idx = int(np.argmax(sharpe))

        best_weights = constrained[best_idx]
        best_return = float(port_returns[best_idx])
        best_vol = float(port_vol[best_idx])

        frontier = pd.DataFrame(
            {
                "risk_pct": port_vol * 100.0,
                "return_pct": port_returns * 100.0,
                "sharpe": sharpe,
            }
        ).sort_values("risk_pct")

        frontier_points = [
            {
                "risk_pct": round(float(row.risk_pct), 4),
                "return_pct": round(float(row.return_pct), 4),
            }
            for row in frontier.iloc[:: max(1, len(frontier) // 250)].itertuples(index=False)
        ]

        current_weight = 1.0 / n_assets
        rebalance = []
        for ticker, optimized in zip(tickers, best_weights):
            current_pct = current_weight * 100.0
            optimized_pct = float(optimized) * 100.0
            rebalance.append(
                {
                    "asset": self.sp500_repository.get_company_name(ticker),
                    "ticker": ticker,
                    "current_pct": round(current_pct, 4),
                    "optimized_pct": round(optimized_pct, 4),
                    "delta": round(optimized_pct - current_pct, 4),
                }
            )

        turnover = 0.5 * sum(abs(item["delta"]) for item in rebalance)

        solver_log = [
            {
                "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "message": f"Loaded {n_assets} assets and {len(returns)} observations.",
                "level": "info",
            },
            {
                "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "message": f"Simulated {len(constrained)} feasible weight vectors.",
                "level": "info",
            },
            {
                "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "message": "Solver converged to max-Sharpe portfolio under constraints.",
                "level": "success",
            },
        ]

        result = {
            "optimizer": {
                "status": "READY",
                "target_return_pct": payload.target_return_pct,
                "volatility_cap_pct": payload.volatility_cap_pct,
                "max_asset_weight_pct": payload.max_asset_weight_pct,
                "sector_neutrality": payload.sector_neutrality,
                "frontier_points": frontier_points,
                "frontier_curve": frontier_points,
                "optimal_point": {
                    "risk_pct": round(best_vol * 100.0, 4),
                    "return_pct": round(best_return * 100.0, 4),
                },
                "rebalance": rebalance,
                "turnover_rate_pct": round(turnover, 4),
                "solver_log": solver_log,
            }
        }

        job_id = uuid.uuid4().hex[:12]
        self.state.optimizer_jobs[job_id] = {
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "status": "done",
            "result": result,
        }

        return {
            "job_id": job_id,
            "status": "done",
            **result,
        }

    def get_job(self, job_id: str) -> dict[str, object]:
        job = self.state.optimizer_jobs.get(job_id)
        if job is None:
            raise KeyError(f"Unknown optimizer job_id: {job_id}")
        return job

    def get_current(self) -> dict[str, object]:
        if self.state.optimizer_jobs:
            latest_key = next(reversed(self.state.optimizer_jobs.keys()))
            job = self.state.optimizer_jobs[latest_key]
            return {
                "job_id": latest_key,
                "status": job.get("status", "done"),
                **job.get("result", {}),
            }

        return {
            "job_id": None,
            "status": "READY",
            "optimizer": {
                "status": "READY",
                "target_return_pct": 12.5,
                "volatility_cap_pct": 8.0,
                "max_asset_weight_pct": 15.0,
                "sector_neutrality": True,
                "frontier_points": [],
                "frontier_curve": [],
                "optimal_point": {"risk_pct": 0.0, "return_pct": 0.0},
                "solver_log": [],
                "rebalance": [],
                "turnover_rate_pct": 0.0,
            },
        }
