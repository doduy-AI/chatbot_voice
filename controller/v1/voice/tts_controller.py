from fastapi import WebSocket, WebSocketDisconnect
from services.Voice.tts_service import tts_service
from services.llm.gemili import ASK_LLM 
import asyncio

llm_gateway = ASK_LLM()

class TTSController:
    async def handle_connection(self, websocket: WebSocket, client_id: str):
        print(f" {client_id} connected.")

        try:
            while True:
                text = await websocket.receive_text()
                print(f"--- [Server] Nhận text từ {client_id}: {text}")
                loop = asyncio.get_event_loop()
                ai_response = await loop.run_in_executor(None, llm_gateway.GEMINI, client_id, text)
                print(ai_response)
                await tts_service.tts_manager(ai_response, client_id)
                from core.connection_manager import manager
                await manager.send_personal_message('{"event": "done"}', client_id)
                print(f"[TTS] Hoàn tất gửi âm thanh cho {client_id}")
        except WebSocketDisconnect:
            print(f" {client_id} đã ngắt kết nối.")
            llm_gateway.clear_session(client_id)
        except Exception as e:  
            print(f"--- [Server] Lỗi kết nối tổng quát: {e}")
        finally:
            print(f"🔚 {client_id} disconnected.")
tts_controller = TTSController()
