from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps import get_services
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/status")
def system_status(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    return services.system.get_shell_metrics()


@router.websocket("/ping")
async def system_ping(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            client_ts = payload.get("client_ts")
            await websocket.send_json(
                {
                    "type": "pong",
                    "client_ts": client_ts,
                    "server_ts": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
            )
    except WebSocketDisconnect:
        return
