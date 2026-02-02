import asyncio

class TTSService:
    def __init__(self):
        pass

    async def stream_audio(self, websocket, text: str):
        try:
            await websocket.send_text(text)
            await websocket.send_text("END_OF_STREAM")
        except Exception as e:
            print(f"--- [WebSocket Error] {e} ---")
            await websocket.send_text("ERROR")


tts_service = TTSService()
