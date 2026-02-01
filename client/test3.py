import asyncio
import websockets
import sys
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 24000

async def start_voice_session():
    uri = "ws://127.0.0.1:6789/api/v1/tts/ws/doduy001"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Kết nối thành công. Nhập text để nói (exit để thoát):")

            while True:
                loop = asyncio.get_event_loop()
                text_input = await loop.run_in_executor(None, sys.stdin.readline)
                text_input = text_input.strip()

                if text_input.lower() == 'exit': break
                if not text_input: continue

                await websocket.send(text_input)
                audio_chunks = []

                # 🔹 Mở 2 file ghi debug
                with open("debug_audio.raw", "wb") as f_audio, open("debug_log.txt", "w", encoding="utf-8") as f_log:
                    while True:
                        response = await websocket.recv()

                        # --- Nếu là dữ liệu bytes (âm thanh) ---
                        if isinstance(response, bytes):
                            f_audio.write(response)
                            audio_chunks.append(response)
                            f_log.write(f"[AUDIO CHUNK] Nhận {len(response)} bytes\n")

                        # --- Nếu là chuỗi ---
                        elif isinstance(response, str):
                            f_log.write(f"[TEXT MESSAGE] {response}\n")

                            if response == "END_OF_STREAM":
                                # Ghép các chunk lại để phát
                                if audio_chunks:
                                    full_audio = b"".join(audio_chunks)
                                    audio_data = np.frombuffer(full_audio, dtype=np.int16)

                                    print(f"🔊 Phát {len(audio_data)/SAMPLE_RATE:.2f}s âm thanh...")
                                    sd.play(audio_data, SAMPLE_RATE)
                                    sd.wait()
                                    print("✅ Phát xong.\n---")
                                break
                            else:
                                print(f"💬 Server message: {response}")

    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    asyncio.run(start_voice_session())
