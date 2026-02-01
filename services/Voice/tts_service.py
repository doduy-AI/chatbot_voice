import numpy as np
import asyncio
import torch
import queue
import threading
import os
from vieneu import FastVieNeuTTS 

# FIX 1: Ép LMDeploy sử dụng template internlm2 để sửa lỗi ngắt sau 960 mẫu
# Phải set biến môi trường này TRƯỚC khi khởi tạo FastVieNeuTTS
os.environ["LMDEPLOY_MODEL_NAME"] = "internlm2"

class TTSService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.VOICE_REPO = "pnnbao-ump/VieNeu-TTS" # Sử dụng bản 0.5B
        self.DEFAULT_VOICE_ID = "Ngoc" 
        self.tts = None

        print(f"--- [Service] Khởi tạo VieNeu-TTS (0.5B) - Tối ưu Max Speed ---")
        self._initialize_model()

    def _initialize_model(self):
        try:
            # FIX 2: Cấu hình đúng tham số FastVieNeuTTS hỗ trợ
            # services/Voice/tts_service.py
            self.tts = FastVieNeuTTS(
                backbone_repo=self.VOICE_REPO,
                backbone_device=self.device,
                memory_util=0.3,           # Set về 0.3 như bạn muốn
                enable_triton=True,        # Bật để đạt max tốc độ
                enable_prefix_caching=True, # Giảm latency cho câu lặp lại
                codec_repo="neuphonic/distill-neucodec",
                codec_device=self.device 
            )
            print("✅ FastVieNeuTTS (0.5B) đã sẵn sàng.")
        except Exception as e:
            print(f"❌ Lỗi khởi tạo Model: {e}")

    # services/Voice/tts_service.py
    def float32_to_pcm16(self, audio_float):
        # Nhân với 32767.0 để đưa về dải âm thanh nghe được
        return (audio_float * 32767.0).clip(-32768, 32767).astype(np.int16).tobytes()

    async def stream_audio(self, websocket, text: str, voice_id: str = None):
        if self.tts is None:
            return

        loop = asyncio.get_running_loop()
        sync_queue = queue.Queue(maxsize=500)
        
        # Lấy dữ liệu giọng nói
        v_id = voice_id or self.DEFAULT_VOICE_ID
        try:
            voice_data = self.tts.get_preset_voice(v_id)
        except:
            # Fallback nếu ID truyền vào sai
            available = self.tts.list_preset_voices()
            voice_data = self.tts.get_preset_voice(available[0][1])

        def run_inference():
            try:
                print(f"--- [Inference] Đang xả luồng cho: {text[:20]}... ---")
                # FIX 4: Giảm max_chars xuống 150 để chunk đầu tiên trả về nhanh hơn
                for chunk in self.tts.infer_stream(text, voice=voice_data, temperature=1.0, max_chars=150):
                    if chunk is not None and len(chunk) > 0:
                        pcm_bytes = self.float32_to_pcm16(chunk)
                        sync_queue.put(pcm_bytes)
                sync_queue.put("END")
            except Exception as e:
                print(f"--- [Inference Error] {e} ---")
                sync_queue.put("ERROR")

        # Chạy inference trong thread riêng để không block Event Loop
        threading.Thread(target=run_inference, daemon=True).start()

        try:
            while True:
                chunk = await loop.run_in_executor(None, sync_queue.get)
                if chunk == "END":
                    await websocket.send_text("END_OF_STREAM")
                    break
                if chunk == "ERROR":
                    await websocket.send_text("ERROR")
                    break
                
                # Gửi dữ liệu nhị phân PCM16 cho client
                await websocket.send_bytes(chunk)
                sync_queue.task_done()
        except Exception as e:
            print(f"❌ Lỗi kết nối WebSocket: {e}")

tts_service = TTSService()