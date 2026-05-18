from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from app.core.state import AppStateStore


class LedgerService:
    def __init__(self, state: AppStateStore) -> None:
        self.state = state

    def get_ledger(self) -> dict[str, Any]:
        ledger = self.state.local_ledger
        holdings: dict[str, dict[str, float]] = {}
        for ticker, entry in ledger.get("holdings", {}).items():
            holdings[str(ticker)] = {
                "quantity": float(entry.get("quantity", 0.0)),
                "avg_cost": float(entry.get("avg_cost", 0.0)),
            }

        history = list(ledger.get("history", []))
        return {
            "cash": round(float(ledger.get("cash", 0.0)), 4),
            "holdings": holdings,
            "history": history,
            "simulated_aum_usd": round(float(self.state.simulated_aum_usd), 2),
        }

    def update_simulated_aum(self, aum_usd: float) -> float:
        clamped = min(max(float(aum_usd), 10_000.0), 100_000_000.0)
        self.state.simulated_aum_usd = clamped
        return clamped

    def apply_fill(
        self,
        ticker: str,
        side: Literal["BUY", "SELL"],
        quantity: float,
        reference_price: float,
        executed_price: float,
        transaction_cost_bps: float,
        slippage_bps: float,
        avg_daily_volume_shares: float,
        participation_rate: float,
    ) -> dict[str, Any]:
        ledger = self.state.local_ledger
        cash = float(ledger.get("cash", 0.0))

        qty = float(quantity)
        ref_px = float(reference_price)
        exec_px = float(executed_price)

        notional = qty * exec_px
        turnover_pct = notional / max(float(self.state.simulated_aum_usd), 1.0)
        tc_cost = notional * (transaction_cost_bps / 10_000.0)

        holdings = ledger.setdefault("holdings", {})
        symbol = ticker.upper()
        entry = holdings.setdefault(symbol, {"quantity": 0.0, "avg_cost": exec_px})

        prev_qty = float(entry.get("quantity", 0.0))
        prev_avg = float(entry.get("avg_cost", exec_px))

        if side == "BUY":
            cash -= notional + tc_cost
            new_qty = prev_qty + qty
            if new_qty > 0:
                weighted_avg = ((prev_qty * prev_avg) + (qty * exec_px)) / new_qty
            else:
                weighted_avg = exec_px
            entry["quantity"] = new_qty
            entry["avg_cost"] = weighted_avg
        else:
            cash += notional - tc_cost
            new_qty = prev_qty - qty
            if new_qty <= 0:
                holdings.pop(symbol, None)
            else:
                entry["quantity"] = new_qty

        ledger["cash"] = cash

        history = ledger.setdefault("history", [])
        history.append(
            {
                "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "ticker": symbol,
                "side": side,
                "quantity": round(qty, 6),
                "reference_price": round(ref_px, 6),
                "executed_price": round(exec_px, 6),
                "notional": round(notional, 6),
                "turnover_pct": round(turnover_pct * 100.0, 6),
                "transaction_cost_bps": round(transaction_cost_bps, 4),
                "transaction_cost_usd": round(tc_cost, 6),
                "slippage_bps": round(slippage_bps, 6),
                "avg_daily_volume_shares": round(avg_daily_volume_shares, 2),
                "participation_rate": round(participation_rate, 6),
            }
        )

        # Keep history bounded while preserving most recent fills.
        if len(history) > 1500:
            del history[: len(history) - 1500]

        return {
            "cash": round(cash, 4),
            "tc_cost_usd": round(tc_cost, 6),
            "turnover_pct": round(turnover_pct * 100.0, 6),
        }
