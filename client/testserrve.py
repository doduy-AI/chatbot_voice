import asyncio
import websockets
import sounddevice as sd
import numpy as np
import json
import wave

TTS_URI = "ws://localhost:6789/api/v1/tts/ws/doduy001"


SAMPLE_RATE = 24000    
CHANNELS = 1
DTYPE = np.int16      

OUTPUT_FILENAME = "/home/doduy/Documents/chatbot_voice/output_audio.wav"

async def tts_client(text: str):
    print("🔌 Đang kết nối tới TTS server...")
    async with websockets.connect(TTS_URI, max_size=None) as ws:
        print("✅ Đã kết nối thành công!")

        # 1️⃣ Gửi text lên server
        payload = json.dumps({"text": text}, ensure_ascii=False)
        await ws.send(payload)
        print(f"📤 Đã gửi text: {text}")
        audio_data = []

        # 2️⃣ Tạo stream âm thanh để phát realtime
        stream = sd.RawOutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=2048,
        )
        stream.start()

        # 3️⃣ Nhận dữ liệu từ server
        try:
            while True:
                message = await ws.recv()

                # 📨 Nếu là JSON (sự kiện)
                if isinstance(message, str):
                    try:
                        msg = json.loads(message)
                        if msg.get("event") == "done":
                            print("✅ Nhận xong âm thanh.")
                            break
                    except json.JSONDecodeError:
                        print(f"[Server msg] {message}")
                    continue

                if isinstance(message, (bytes, bytearray)):
                    if len(message) == 0:
                        continue  # bỏ qua chunk rỗng

                    # Ghi trực tiếp vào buffer âm thanh (realtime)
                    stream.write(message)
                    audio_data.append(message)
                    print(f"🎧 Phát {len(message)} bytes...")

        except websockets.ConnectionClosed:
            print("⚠️ Kết nối WebSocket bị đóng.")
        except Exception as e:
            print(f"❌ Lỗi khi nhận dữ liệu: {e}")
        finally:
            stream.stop()
            stream.close()
            print("🔚 Đã dừng stream âm thanh.")

        if audio_data:
            print(f"\n💾 Đang ghi vào file: {OUTPUT_FILENAME}")
            with wave.open(OUTPUT_FILENAME, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2) # 2 bytes cho 16-bit
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(b''.join(audio_data))
            print("✨ Đã lưu file thành công!")
        else:
            print("⚠️ Không có dữ liệu âm thanh để lưu.")

        print("🏁 Hoàn tất phiên TTS.")


# ==========================
# 🚀 Chạy thử
# ==========================
text = "hỏi tên trong tienegs anh thì hỏi ntn "
if __name__ == "__main__":
    asyncio.run(tts_client(text))