import asyncio
import websockets
import sounddevice as sd
import numpy as np

TTS_URI = "ws://1.208.108.242:58536/api/v1/tts/ws/doduy001"

async def receive_audio():
    async with websockets.connect(TTS_URI) as websocket:
        print("🔌 Đã kết nối tới server TTS.")

        # Gửi câu test để server đọc
        text = "Xin chào, mình là robot nói tiếng Việt! , bạn tên là gì bạn có muốn đấm nhau không "
        await websocket.send(text)
        print(f"📤 Đã gửi text: {text}\n")

        audio_buffer = bytearray()
        while True:
            data = await websocket.recv()

            # Nếu là tín hiệu kết thúc
            if isinstance(data, str):
                if data == "END_OF_STREAM":
                    print("✅ Nhận xong toàn bộ âm thanh.")
                    break
                elif data == "ERROR":
                    print("❌ Server báo lỗi.")
                    break
                else:
                    print(f"📩 Tin nhắn từ server: {data}")
            else:
                # data là bytes PCM16
                print(f"🎵 Nhận {len(data)} bytes âm thanh.")
                audio_buffer.extend(data)

        # Sau khi nhận đủ -> phát lại âm thanh
        print(f"▶️ Tổng cộng nhận được {len(audio_buffer)} bytes, đang phát lại...")
        audio_np = np.frombuffer(audio_buffer, dtype=np.int16)
        sd.play(audio_np, samplerate=24000)
        sd.wait()
        print("🔚 Phát xong.")

if __name__ == "__main__":
    asyncio.run(receive_audio())
