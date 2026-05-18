from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_services
from app.schemas.contracts import AgentQueryRequest
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/brief")
async def agent_brief(services: ServiceContainer = Depends(get_services)) -> dict[str, object]:
    payload = await services.agent.get_agent_payload()
    return {"agent": payload["agent"]}


@router.get("/stream")
def agent_stream(
    limit: int = Query(default=100, ge=1, le=1000),
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return {"agent": {"worker_stream": services.agent.get_worker_stream(limit=limit)}}


@router.post("/query")
async def agent_query(
    payload: AgentQueryRequest,
    services: ServiceContainer = Depends(get_services),
) -> dict[str, object]:
    return await services.agent.answer_query(payload.query)


@router.websocket("/stream/ws")
async def agent_stream_ws(
    websocket: WebSocket,
    services: ServiceContainer = Depends(get_services),
) -> None:
    await websocket.accept()

    async def stream_text(channel: str, text: str, suggested_command: str | None = None) -> None:
        await websocket.send_json({"type": "start", "channel": channel})
        for token in services.agent.stream_tokens(text):
            await websocket.send_json({"type": "token", "channel": channel, "token": token})
            await asyncio.sleep(0.02)

        payload: dict[str, object] = {"type": "done", "channel": channel}
        if suggested_command is not None:
            payload["suggested_command"] = suggested_command
        await websocket.send_json(payload)

    try:
        brief_text = await services.agent.get_daily_brief_text()
        await stream_text("brief", brief_text, "rebalance_portfolio(mode='hrp_meta_kelly', guardrails='strict')")

        while True:
            message = await websocket.receive_json()
            query = str(message.get("query", "")).strip()
            if not query:
                await websocket.send_json(
                    {
                        "type": "error",
                        "channel": "query",
                        "message": "Query cannot be empty.",
                    }
                )
                continue

            response = await services.agent.answer_query(query)
            await stream_text(
                "query",
                str(response.get("answer", "")),
                str(response.get("suggested_command", "")),
            )
    except WebSocketDisconnect:
        return
