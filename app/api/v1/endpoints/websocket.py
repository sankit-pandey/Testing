"""WebSocket endpoint for real-time pipeline progress.

Design ref: `Technical_Design_Document.md` §4.2 (`WS /api/v1/ws/{client_id}`);
`Architecture_Diagrams.md` §10. Story 3.1.

Protocol: client connects, then sends `{"action": "subscribe", "artifactId":
"..."}` / `{"action": "unsubscribe", "artifactId": "..."}` JSON messages to
control which artifact channels it receives events for. Any authenticated
role may subscribe (progress viewing is a read-only action, permitted for
`viewer` per `Requirements_Document.md` §2.2).
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import InvalidTokenError, decode_token
from app.services.event_bus import ArtifactEventSubscriber

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, token: str) -> None:
    try:
        decode_token(token, expected_type="access")
    except InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    subscriptions: dict[str, asyncio.Task] = {}

    async def forward(artifact_id: str) -> None:
        async with ArtifactEventSubscriber(artifact_id) as subscriber:
            async for event in subscriber.listen():
                await websocket.send_json(event)

    try:
        while True:
            message = await websocket.receive_json()
            action = message.get("action")
            artifact_id = message.get("artifactId")
            if not artifact_id:
                continue
            if action == "subscribe" and artifact_id not in subscriptions:
                subscriptions[artifact_id] = asyncio.create_task(forward(artifact_id))
            elif action == "unsubscribe" and artifact_id in subscriptions:
                subscriptions.pop(artifact_id).cancel()
    except WebSocketDisconnect:
        pass
    finally:
        for task in subscriptions.values():
            task.cancel()
