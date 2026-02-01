from fastapi import WebSocket
from typing import Dict

class ConnectionManager:
    def __init__(self):
        # Lưu trữ: { "ID_người_dùng": đối_tượng_websocket }
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Người dùng {client_id} đã online. Tổng: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"{client_id} đã offline.")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
    async def send_audio_to_client(self, data: bytes, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_bytes(data)

manager = ConnectionManager()