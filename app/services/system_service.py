from __future__ import annotations

import time

from app.core.config import Settings
from app.utils.time_utils import now_est_label


class SystemService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_shell_metrics(self) -> dict[str, dict[str, float | int | str]]:
        tick = int(time.time())
        latency_ms = 8 + (tick % 13)
        unread_count = tick % 4

        return {
            "system": {
                "latency_ms": latency_ms,
                "clock_est": now_est_label(),
                "status": "ONLINE",
            },
            "alerts": {
                "unread_count": unread_count,
            },
            "user": {
                "initials": self.settings.default_user_initials,
            },
        }
