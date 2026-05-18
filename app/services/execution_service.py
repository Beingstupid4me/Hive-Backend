from __future__ import annotations

import math
from datetime import datetime, timezone

from app.core.config import Settings
from app.core.state import AppStateStore
from app.providers.base import MarketDataProvider
from app.repositories.sp500 import Sp500Repository
from app.schemas.contracts import OrderRequest
from app.services.ledger_service import LedgerService


class ExecutionService:
    TC_BPS = 5.0

    def __init__(
        self,
        settings: Settings,
        provider: MarketDataProvider,
        sp500_repository: Sp500Repository,
        state: AppStateStore,
        ledger: LedgerService,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.sp500_repository = sp500_repository
        self.state = state
        self.ledger = ledger
        self._seed_orders()

    def _seed_orders(self) -> None:
        if self.state.execution_orders:
            return

        now = datetime.now(timezone.utc).replace(microsecond=0)
        for i, payload in enumerate(
            [
                ("NVDA", "BUY", 500, 784.18, "FILLED", "ARCA"),
                ("AAPL", "BUY", 1200, 212.44, "ROUTED", "NASDAQ"),
                ("XOM", "SELL", 900, 112.11, "PENDING", "CBOE"),
                ("MSFT", "BUY", 450, 417.21, "CANCELLED", "BATS"),
            ],
            start=1,
        ):
            ticker, side, qty, price, status, route = payload
            self.state.execution_orders.append(
                {
                    "id": str(i),
                    "timestamp": (now).isoformat(),
                    "ticker": ticker,
                    "side": side,
                    "quantity": qty,
                    "price": price,
                    "status": status,
                    "route": route,
                }
            )

    def get_connectivity(self) -> dict[str, object]:
        mode_suffix = "HIST" if self.settings.historical_data else "LIVE"
        return {
            "execution": {
                "connectivity_endpoint": f"NY4-{mode_suffix}",
                "connectivity_latency_ms": 0.4 if not self.settings.historical_data else 1.2,
                "quick_size_options": [25, 50, 75, "MAX"],
            }
        }

    def _average_daily_volume_shares(self, ticker: str, lookback: int = 21) -> float:
        try:
            history = self.sp500_repository.get_history(ticker, lookback=lookback)
        except (FileNotFoundError, ValueError):
            return 1_000_000.0

        if history.empty or "Volume" not in history.columns:
            return 1_000_000.0

        return float(max(history["Volume"].tail(lookback).mean(), 1_000.0))

    def _estimate_slippage_bps(
        self,
        order_notional: float,
        avg_daily_volume_shares: float,
        reference_price: float,
    ) -> tuple[float, float]:
        adv_notional = max(avg_daily_volume_shares * max(reference_price, 0.01), 1.0)
        participation = max(0.0, min(order_notional / adv_notional, 1.0))

        slippage_bps = 1.5 + 65.0 * math.sqrt(participation)
        if participation > 0.05:
            slippage_bps += (participation - 0.05) * 550.0

        return min(slippage_bps, 350.0), participation

    @staticmethod
    def _execution_price(reference_price: float, side: str, slippage_bps: float) -> float:
        side_sign = 1.0 if side == "BUY" else -1.0
        return reference_price * (1.0 + side_sign * (slippage_bps / 10_000.0))

    async def get_friction_projection(self, aum_usd: float, ticker: str) -> dict[str, object]:
        simulated_aum = self.ledger.update_simulated_aum(aum_usd)
        quote = await self.provider.get_quote(ticker)
        ref_price = float(quote.get("close", 100.0))

        # Use a representative per-name rebalance trade to estimate liquidity pressure.
        trade_notional = simulated_aum * 0.003
        avg_daily_volume_shares = self._average_daily_volume_shares(ticker)
        slippage_bps, participation = self._estimate_slippage_bps(
            order_notional=trade_notional,
            avg_daily_volume_shares=avg_daily_volume_shares,
            reference_price=ref_price,
        )

        aum_scale = max(simulated_aum / 10_000.0, 1.0)
        scale_log = math.log10(aum_scale)

        base_return_pct = 18.0
        base_sharpe = 1.35

        return_drag_pct = (2.8 * scale_log) + (slippage_bps * 0.04)
        sharpe_drag = (0.22 * scale_log) + (slippage_bps / 260.0)

        projected_return_pct = max(1.0, base_return_pct - return_drag_pct)
        projected_sharpe = max(0.2, base_sharpe - sharpe_drag)

        return {
            "execution": {
                "capacity": {
                    "aum_usd": round(simulated_aum, 2),
                    "reference_ticker": ticker.upper(),
                    "sample_trade_notional_usd": round(trade_notional, 2),
                    "avg_daily_volume_shares": round(avg_daily_volume_shares, 2),
                    "participation_rate": round(participation, 6),
                    "tc_bps": round(self.TC_BPS, 3),
                    "slippage_bps": round(slippage_bps, 3),
                    "total_cost_bps": round(self.TC_BPS + slippage_bps, 3),
                    "projected_annual_return_pct": round(projected_return_pct, 3),
                    "projected_sharpe": round(projected_sharpe, 4),
                }
            }
        }

    def get_ledger_payload(self) -> dict[str, object]:
        return {
            "execution": {
                "ledger": self.ledger.get_ledger(),
            }
        }

    async def get_order_book(self, ticker: str) -> dict[str, object]:
        quote = await self.provider.get_quote(ticker)
        mid = float(quote.get("close", 100.0))
        spread_step = max(mid * 0.00005, 0.01)

        bids = [
            {"price": round(mid - spread_step * (i + 1), 4), "size": int(300 + (i + 1) * 140)}
            for i in range(12)
        ]
        asks = [
            {"price": round(mid + spread_step * (i + 1), 4), "size": int(280 + (i + 1) * 130)}
            for i in range(12)
        ]

        spread = asks[0]["price"] - bids[0]["price"] if bids and asks else 0.0

        return {
            "execution": {
                "l2_bids": bids,
                "l2_asks": asks,
                "spread": round(spread, 5),
            }
        }

    async def get_candles(self, ticker: str, timeframe: str = "1d", limit: int = 60) -> dict[str, object]:
        candles = await self.provider.get_candles(ticker=ticker, timeframe=timeframe, limit=limit)
        return {
            "execution": {
                "candles": candles,
                "timeframe": timeframe,
            }
        }

    async def get_positions(self) -> dict[str, object]:
        ledger = self.ledger.get_ledger()
        rows: list[dict[str, object]] = []
        for ticker, position in ledger["holdings"].items():
            quantity = float(position.get("quantity", 0.0))
            if quantity <= 0:
                continue

            avg_entry = float(position.get("avg_cost", 0.0))
            quote = await self.provider.get_quote(ticker)
            mark = float(quote.get("close", avg_entry))
            pnl = (mark - avg_entry) * quantity

            rows.append(
                {
                    "instrument": ticker,
                    "side": "LONG",
                    "size": abs(round(quantity, 4)),
                    "entry_price": round(avg_entry, 4),
                    "mark_price": round(mark, 4),
                    "unrealized_pnl": round(pnl, 2),
                }
            )

        return {"execution": {"positions": rows[:20]}}

    def get_orders(self, limit: int = 200) -> dict[str, object]:
        orders = list(self.state.execution_orders)
        return {"execution": {"orders": orders[-limit:]}}

    async def place_order(self, payload: OrderRequest) -> dict[str, object]:
        quote_price = payload.price
        if quote_price is None:
            quote = await self.provider.get_quote(payload.ticker)
            quote_price = float(quote.get("close", 0.0))

        reference_price = float(quote_price)
        quantity = float(payload.quantity)
        notional = quantity * reference_price

        avg_daily_volume_shares = self._average_daily_volume_shares(payload.ticker)
        slippage_bps, participation = self._estimate_slippage_bps(
            order_notional=notional,
            avg_daily_volume_shares=avg_daily_volume_shares,
            reference_price=reference_price,
        )
        executed_price = self._execution_price(reference_price, payload.side, slippage_bps)

        ledger_update = self.ledger.apply_fill(
            ticker=payload.ticker,
            side=payload.side,
            quantity=quantity,
            reference_price=reference_price,
            executed_price=executed_price,
            transaction_cost_bps=self.TC_BPS,
            slippage_bps=slippage_bps,
            avg_daily_volume_shares=avg_daily_volume_shares,
            participation_rate=participation,
        )

        order = {
            "id": str(len(self.state.execution_orders) + 1),
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "ticker": payload.ticker.upper(),
            "side": payload.side,
            "quantity": quantity,
            "price": round(float(executed_price), 6),
            "reference_price": round(reference_price, 6),
            "status": "FILLED",
            "route": "SMART",
            "algo": payload.algo,
            "transaction_cost_bps": round(self.TC_BPS, 3),
            "transaction_cost_usd": ledger_update["tc_cost_usd"],
            "slippage_bps": round(slippage_bps, 6),
            "participation_rate": round(participation, 6),
            "turnover_pct": ledger_update["turnover_pct"],
        }

        self.state.execution_orders.append(order)
        return {
            "accepted": True,
            "order": order,
            "ledger": self.ledger.get_ledger(),
        }

    async def get_execution_payload(self, ticker: str, timeframe: str) -> dict[str, object]:
        connectivity = self.get_connectivity()
        book = await self.get_order_book(ticker)
        candles = await self.get_candles(ticker=ticker, timeframe=timeframe, limit=60)
        positions = await self.get_positions()
        orders = self.get_orders(limit=100)
        friction = await self.get_friction_projection(self.state.simulated_aum_usd, ticker)
        ledger_payload = self.get_ledger_payload()

        quote = await self.provider.get_quote(ticker)

        return {
            "execution": {
                **connectivity["execution"],
                **book["execution"],
                **candles["execution"],
                **positions["execution"],
                **orders["execution"],
                **ledger_payload["execution"],
                **friction["execution"],
                "order_side": "BUY",
                "order_ticker": ticker.upper(),
                "order_quantity": 2500,
                "order_price": round(float(quote.get("close", 0.0)), 4),
                "order_algo": "VWAP",
            }
        }
