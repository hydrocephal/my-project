from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import chat as chat_service

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        websocket_user = await chat_service.websocket_connection_logic(websocket)
        if websocket_user is None:
            await websocket.close(code=4003)  # Forbidden
            return
    except (RuntimeError, WebSocketDisconnect):
        pass
