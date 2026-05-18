from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


def _default_ledger() -> dict[str, Any]:
    return {
        "cash": 100_000.0,
        "holdings": {},
        "history": [],
    }


@dataclass
class AppStateStore:
    execution_orders: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=1000))
    risk_active_orders: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=500))
    agent_worker_stream: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=2000))
    optimizer_jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    local_ledger: dict[str, Any] = field(default_factory=_default_ledger)
    simulated_aum_usd: float = 100_000.0
