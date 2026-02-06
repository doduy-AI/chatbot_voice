import asyncio
import aiohttp
import io
import wave
from urllib.parse import quote
from core.config import settings
from core.connection_manager import manager
from utils.lang_detector import split_and_label


class TTSService:
    def __init__(self):
        self.URL_VI = settings.URL_VI
        self.URL_EN = settings.URL_EN

    async def tts_manager(self, full_text: str, client_id: str):
        print(f"🗣️ Bắt đầu TTS cho {client_id}: {full_text}")

        segments = split_and_label(full_text)
        manager.send_personal_message("text sau khi gắn tab"+segments,client_id)
        audio_queue = asyncio.Queue()

        # ============================
        # 1️⃣ Lấy dữ liệu audio từ API
        # ============================
        async def fetch_audio():
            async with aiohttp.ClientSession() as session:
                for seg in segments:
                    lang = seg["lang"]
                    text = seg["text"].strip()
                    if not text:
                        continue

                    target_url = self.URL_VI if lang == "VI" else self.URL_EN
                    url = f"{target_url}?text={quote(text)}"
                    print(f"🎯 [{lang}] Gọi tới: {url}")

                    try:
                        async with session.get(url, timeout=30) as response:
                            first_chunk_of_seg = True
                            async for chunk in response.content.iter_chunked(2048):
                                if not chunk:
                                    continue

                                if first_chunk_of_seg:
                                    try:
                                        with wave.open(io.BytesIO(chunk), "rb") as wf:
                                            sr = wf.getframerate()
                                            ch = wf.getnchannels()
                                            bit = wf.getsampwidth() * 8
                                            # print(f"🔍 [{lang}] WAV Info: {sr} Hz | {ch} ch | {bit}-bit")
                                    except Exception as e:
                                        print(f"⚠️ [{lang}] Không đọc được header WAV: {e}")

                                    # Bỏ header WAV (44 bytes) ở chunk đầu
                                    data = chunk[44:]
                                    first_chunk_of_seg = False
                                else:
                                    data = chunk

                                await audio_queue.put((lang, data))

                    except Exception as e:
                        print(f"--- [Lỗi tải {lang}]: {e}")

            # Đánh dấu kết thúc hàng đợi
            await audio_queue.put(None)

        # ============================
        # 2️⃣ Stream dữ liệu ra WebSocket
        # ============================
        async def stream_audio():
            print("--- Bắt đầu gửi luồng Bytes âm thanh ---")
            while True:
                item = await audio_queue.get()
                if item is None:
                    break

                lang, data = item
                if not data:
                    continue

                # print(f"📦 [{lang}] Nhận được: {len(data)} bytes")
                try:
                    # Gửi dữ liệu tới đúng client
                    await manager.send_audio_to_client(data, client_id)
                except Exception as e:
                    print(f"❌ [Gửi lỗi tới {client_id}]: {e}")
                    break

                audio_queue.task_done()

            # Sau khi gửi xong toàn bộ audio
            await manager.send_personal_message('{"event": "done"}', client_id)
            print(f"✅ [Server] Gửi xong toàn bộ âm thanh cho {client_id}")

        # ============================
        # 3️⃣ Chạy song song 2 tác vụ
        # ============================
        await asyncio.gather(fetch_audio(), stream_audio())


tts_service = TTSService()
