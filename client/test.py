import asyncio
import websockets
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import speech_recognition as sr
import time
import queue
import json

# ====== CẤU HÌNH ======
SAMPLE_RATE_TTS = 24000  
REC_SAMPLE_RATE = 44100
DURATION = 5
TTS_URI = "ws://localhost:6789/api/v1/tts/ws/doduy001"

# ====== STT (Speech to Text) ======
def record_audio(duration=DURATION, fs=REC_SAMPLE_RATE, filename="input.wav"):
    print(f"\n🎤 Ghi âm {duration}s... (Mời bạn nói)")
    try:    
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
        sd.wait()
        write(filename, fs, (recording * 32767).astype(np.int16))
        return filename
    except Exception as e:
        print(f"❌ Lỗi ghi âm: {e}")
        return None

def stt(audio_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='vi-VN')
            print(f"👤 Bạn nói: {text}")
            return text
    except Exception:
        print("❓ Không nghe rõ...")
        return None

import asyncio
import websockets
import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write

# ====== CẤU HÌNH ======
TTS_URI = "ws://localhost:6789/api/v1/tts/ws/doduy001"

# --- Giữ nguyên các hàm record_audio và stt của Duy ---

async def handle_text_io(websocket, text_input):
    """Gửi 1 text và nhận lại 1 text từ Server"""
    try:
        # 1. Gửi text lên server
        await websocket.send(text_input)
        print(f"🚀 Đã gửi: {text_input}")

        # 2. Đợi nhận đúng 1 phản hồi text từ server
        response = await websocket.recv()
        
        if isinstance(response, str):
            print(f"🤖 Robot phản hồi: {response}")
            # Sau khi có text này, Duy có thể ném nó vào hàm phát âm thanh HTTP của Duy
            # await play_audio_from_http(response) 
        else:
            print(" Cảnh báo: Server trả về dữ liệu binary nhưng logic đang đợi text.")

    except Exception as e:
        print(f" Lỗi khi trao đổi dữ liệu: {e}")

async def voice_loop():
    print("🤖 Robot sẵn sàng (Chế độ Text IO)!")
    try:
        async with websockets.connect(TTS_URI) as websocket:
            print(f" Đã kết nối tới {TTS_URI}")
            while True:
                # 1. Thu âm & Chuyển thành văn bản
                filename = record_audio()
                if not filename: continue
                
                text_input = stt(filename)
                if not text_input: continue
                
                # 2. Gửi và Nhận phản hồi
                await handle_text_io(websocket, text_input)

                await asyncio.sleep(0.5)
    except Exception as e:
        print(f" Lỗi kết nối: {e}")

if __name__ == "__main__":
    asyncio.run(voice_loop())