from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from controller.v1.voice.tts_controller import tts_controller
from core.connection_manager import manager
import starlette.status as status

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def tts_ws_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        await tts_controller.handle_connection(websocket, client_id)
    except WebSocketDisconnect:
        print(f"⚠️ Client {client_id} đã ngắt kết nối.")
    finally:
        manager.disconnect(client_id)
