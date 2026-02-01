import asyncio
import websockets
import sys
from scipy.io.wavfile import write
import soundfile as sf
import speech_recognition as sr
import sounddevice as sd


def stt(audio_path):
    print("cloud   Đang nhận diện giọng nói...")
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='vi-VN')
            return text
    except sr.UnknownValueError:
        return None # Trả về None để code chính biết mà bỏ qua
    except sr.RequestError:
        print(" Lỗi kết nối Google STT")
        return None


DURATION = 5 
REC_SAMPLE_RATE = 44100

def record_audio(duration=DURATION, fs=REC_SAMPLE_RATE, filename="input.wav"):
    print(f"\n Đang ghi âm {duration}s... (Mời bạn nói)")
    frames = int(duration * fs)
    try:
        with sd.InputStream(samplerate=fs, channels=1) as stream:
            data, overflowed = stream.read(frames)
            
        if overflowed:
            print(" Cảnh báo: Tràn bộ nhớ đệm Mic.")
        
        # Chuyển đổi sang chuẩn WAV int16
        write(filename, fs, (data * 32767).astype(np.int16))
        return filename
    except Exception as e:
        print(f" Lỗi ghi âm: {e}")
        return None
async def start_voice_session():
    uri = "ws://27.64.192.151:63334/api/v1/tts/ws/doduy002"
    
    try:
        # 1. Kết nối một lần duy nhất tại đây
        async with websockets.connect(uri, origin="http://127.0.0.1:6789") as websocket:
            print("✅ ĐÃ MỞ ĐƯỜNG TRUYỀN RIÊNG (PERSISTENT CONNECTION)")
            print("Nhập nội dung cần nói (hoặc gõ 'exit' để thoát):")

            while True:
                # 2. Đợi Duy nhập text từ bàn phím
                # Dùng loop.run_in_executor để không làm treo loop async khi đợi nhập liệu
                loop = asyncio.get_event_loop()
                text_input = await loop.run_in_executor(None, sys.stdin.readline)
                text_input = text_input.strip()

                if text_input.lower() == 'exit':
                    break
                
                if not text_input:
                    continue

                # 3. Gửi text lên Server qua đường ống đang mở
                await websocket.send(text_input)
                print(f"🚀 Đang gửi: {text_input}")

                # 4. Đợi nhận luồng binary trả về
                # Vòng lặp nhận dữ liệu cho ĐẾN KHI thấy END_OF_STREAM
                while True:
                    response = await websocket.recv()
                    
                    if isinstance(response, str):
                        # Nếu nhận được chữ thì in ra
                        if response == "END_OF_STREAM":
                            print("🏁 Xong câu này.\n---")
                            break
                        else:
                            print(f"💬 Nội dung server: {response}") # <--- Dòng này sẽ hiện Text
                    else:
                        # Nếu nhận được bytes thì báo số lượng
                        print(f"📦 Nhận chunk binary: {len(response)} bytes")

    except Exception as e:
        print(f"❌ Mất kết nối: {e}")

if __name__ == "__main__":
    asyncio.run(start_voice_session())