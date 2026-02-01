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
TTS_URI = "ws://116.106.20.52:23658/api/v1/tts/ws/doduy001"

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

# ====== TTS (Text to Speech) - BẢN BỔ SUNG LOG DEBUG ======
async def tts_speak(websocket, text):
    start_time = time.perf_counter()
    
    # 1. Gửi yêu cầu
    await websocket.send(text)
    print(f"🚀 Đã gửi: '{text}'")
    
    audio_queue = queue.Queue()
    first_chunk_received = False
    total_samples = 0
    chunk_count = 0
    
    def callback(outdata, frames, time_info, status):
        try:
            data = audio_queue.get_nowait()
            if len(data) < len(outdata):
                outdata[:len(data), 0] = data
                outdata[len(data):, 0] = 0
            else:
                outdata[:, 0] = data[:len(outdata)]
        except queue.Empty:
            outdata.fill(0)

    with sd.OutputStream(samplerate=SAMPLE_RATE_TTS, channels=1, dtype='int16', callback=callback, blocksize=1024) as stream:
        print("🔊 Đang đợi luồng âm thanh từ Server...")
        
        while True:
            try:
                response = await websocket.recv()
                
                # CASE 1: Nhận tin nhắn văn bản (Control/Status)
                if isinstance(response, str):
                    print(f"📝 [TEXT FRAME]: {response}")
                    if response == "END_OF_STREAM":
                        print(f"🏁 Nhận tín hiệu kết thúc. Tổng mẫu nhận được: {total_samples}")
                        while not audio_queue.empty():
                            await asyncio.sleep(0.1)
                        await asyncio.sleep(0.5)
                        break
                    continue
                
                # CASE 2: Nhận dữ liệu âm thanh (Binary)
                chunk_count += 1
                if not first_chunk_received:
                    latency = (time.perf_counter() - start_time) * 1000
                    print(f"⏱️ TTFA (Độ trễ chunk đầu): {latency:.2f} ms")
                    first_chunk_received = True
                
                # Giải mã dữ liệu (Sử dụng int16 vì server của bạn đã convert pcm16)
                chunk = np.frombuffer(response, dtype='int16')
                total_samples += len(chunk)
                
                # --- LOG DEBUG CHI TIẾT ---
                v_min, v_max = np.min(chunk), np.max(chunk)
                print(f"📦 [Chunk #{chunk_count}] Size: {len(chunk)} | Min: {v_min} | Max: {v_max}")
                
                # Nếu biên độ Min/Max đều bằng 0, có nghĩa là server đang gửi đoạn im lặng
                if v_min == 0 and v_max == 0:
                    print("⚠️ Cảnh báo: Chunk này hoàn toàn là khoảng lặng!")

                # Đưa vào hàng đợi để phát
                for i in range(0, len(chunk), 1024):
                    sub_chunk = chunk[i:i+1024]
                    if len(sub_chunk) < 1024:
                        padded = np.zeros(1024, dtype='int16')
                        padded[:len(sub_chunk)] = sub_chunk
                        audio_queue.put(padded)
                    else:
                        audio_queue.put(sub_chunk)
                        
            except websockets.exceptions.ConnectionClosed:
                print("❌ LỖI: Server ngắt kết nối WebSocket đột ngột.")
                break
            except Exception as e:
                print(f"❌ LỖI TRONG LUỒNG NHẬN: {e}")
                break

    print(f"✅ Robot nói xong. Tổng cộng nhận {chunk_count} chunks.")

async def voice_loop():
    print("🤖 Robot VieNeu-TTS sẵn sàng!")
    try:
        async with websockets.connect(TTS_URI) as websocket:
            print(f"🔗 Đã kết nối tới {TTS_URI}")
            while True:
                filename = record_audio()
                if not filename: continue
                
                text_input = stt(filename)
                if not text_input: continue
                
                await tts_speak(websocket, text_input)
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")

if __name__ == "__main__":
    asyncio.run(voice_loop())