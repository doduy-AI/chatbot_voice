from fastapi import WebSocket, WebSocketDisconnect
from services.Voice.tts_service import tts_service
from services.llm.gemili import ASK_LLM 
from utils.lang_detector import split_and_label

import asyncio
llm_gateway = ASK_LLM()

class TTSController:
    async def handle_connection(self, websocket: WebSocket, client_id: str):
        try:
            while True:
                text = await websocket.receive_text()
                print(f"--- [Server] Nhận text từ {client_id}: {text}")
                loop = asyncio.get_event_loop()
                # ai_response = await loop.run_in_executor(None, llm_gateway.GEMINI ,client_id,text)
                print("text nhận từ client ", text)
                ai_response = "Nếu trong log thỉnh thoảng vẫn hiện lỗi coroutine was never awaited, đó là vì các đoạn text sau khi tách xong được đẩy vào hàm nói nhưng không có await."
                textloc = split_and_label(ai_response)
                print(textloc)
        except WebSocketDisconnect:
            print(f"--- [Server] {client_id} đã ngắt kết nối ---")
            llm_gateway.clear_session(client_id)
        except Exception as e:  
            print(f"--- [Server] Lỗi kết nối tổng quát: {e}")

tts_controller = TTSController()
