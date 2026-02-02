import asyncio
import websockets
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import speech_recognition as sr
import time
import pyaudio
import requests
from urllib.parse import quote

# ====== KHỞI TẠO CẤU HÌNH (Chỉ làm 1 lần) ======
SAMPLE_RATE_TTS = 24000  
REC_SAMPLE_RATE = 44100
DURATION = 5
TTS_URI = "ws://localhost:6789/api/v1/tts/ws/doduy001"
STREAM_URL = "http://192.168.1.35:8001/stream"

# Khởi tạo PyAudio ở Global để dùng chung cho toàn bộ chương trình
p = pyaudio.PyAudio()
stream_player = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE_TTS, output=True)

# --- Các hàm STT giữ nguyên ---
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

async def handle_text_io(websocket, text_input):
    
    """Gửi text và phát âm thanh từ phản hồi"""
    try:
        # 1. Gửi và nhận Text từ Chatbot
        await websocket.send(text_input)
        print(f"🚀 Gửi: {text_input}")

        response = await websocket.recv()
        
        if isinstance(response, str):
            print(f"🤖 Robot: {response}")
            
            # 2. Gọi API Stream âm thanh
            url = f"{STREAM_URL}?text={quote(response)}"
            start_time = time.perf_counter()
            first_chunk = True 
            
            try:
                with requests.get(url, stream=True, timeout=20) as r:
                    r.raise_for_status() 
                    for chunk in r.iter_content(chunk_size=2048): 
                        if chunk:
                            if first_chunk:
                                latency = time.perf_counter() - start_time
                                print(f"✅ Phát tiếng sau: {latency:.2f}s")
                                # CHỈ PHÁT PHẦN SAU HEADER
                                stream_player.write(chunk[44:]) 
                                first_chunk = False
                            else:
                                stream_player.write(chunk)

            except Exception as e:
                print(f"Lỗi stream âm thanh: {e}")
            
            print("--- Kết thúc nói ---")

        else:
            print(" Cảnh báo: Nhận dữ liệu Binary không mong muốn.")

    except Exception as e:
        print(f" Lỗi trao đổi: {e}")

async def voice_loop():
    print("🤖 Robot sẵn sàng (No-Pop Mode)!")
    try:
        async with websockets.connect(TTS_URI) as websocket:
            print(f"🔗 Đã nối ống tới {TTS_URI}")
            while True:
                filename = record_audio()
                if not filename: continue
                
                text_input = stt(filename)
                if not text_input: continue
                
                await handle_text_io(websocket, text_input)
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f" Lỗi kết nối: {e}")
    finally:
        # CHỈ ĐÓNG KHI TẮT HẲN CHƯƠNG TRÌNH
        stream_player.stop_stream()
        stream_player.close()
        p.terminate()

if __name__ == "__main__":
    asyncio.run(voice_loop())