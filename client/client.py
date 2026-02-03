import asyncio
import websockets
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import speech_recognition as sr
import time
import pyaudio
import requests
import time, datetime, random
from urllib.parse import quote
from STT import record, OUTPUT_WAV
import termios, sys, atexit

# Hàm ẩn echo Ctrl+C trên terminal
def disable_ctrl_c_echo():
    fd = sys.stdin.fileno()
    attrs = termios.tcgetattr(fd)
    attrs[3] = attrs[3] & ~termios.ECHOCTL  
    termios.tcsetattr(fd, termios.TCSANOW, attrs)

def restore_terminal():
    fd = sys.stdin.fileno()
    attrs = termios.tcgetattr(fd)
    attrs[3] = attrs[3] | termios.ECHOCTL
    termios.tcsetattr(fd, termios.TCSANOW, attrs)

disable_ctrl_c_echo()
atexit.register(restore_terminal)

# ====== KHỞI TẠO CẤU HÌNH (Chỉ làm 1 lần) ======
SAMPLE_RATE_TTS = 24000  
REC_SAMPLE_RATE = 44100
DURATION = 5
TTS_URI = "ws://192.168.1.6:6789/api/v1/tts/ws/doduy001"
STREAM_URL = "http://192.168.1.35:8001/stream"

HELLO_MESSAGES = [
    "Xin chào! Tôi là Emily, tôi có thể giúp gì cho bạn?",
    "Chào bạn nhé! Emily đã sẵn sàng rồi đây.",
    "Hello! Tôi là Emily, hôm nay tôi giúp được gì cho bạn?",
    "Xin chào bạn, rất vui được gặp bạn!",
    "Emily đây! Bạn cần tôi hỗ trợ việc gì nào?",
    "Chào bạn, tôi đang lắng nghe đây ",
    "Xin chào! Bắt đầu thôi nào ",
    "Hey! Emily đã sẵn sàng phục vụ bạn.",
    "Chào bạn nhé, bạn muốn hỏi điều gì?",
    "Xin chào! Tôi là Emily, rất hân hạnh được giúp bạn."
]

FEEDBACK_MESSAGE = [
    "Xin lỗi, bạn có cần tôi giúp gì không?",
    "Mình không nghe thấy bạn nói gì, bạn có chuyện gì cần mình giải đáp cho không?",
    "Có vẻ là bạn hơi yếu đuối, bạn cần mình giúp gì không?",
    "Mình không nghe rõ lắm, bạn có thể nói lại được không?",
    "Bạn cần mình giúp gì không nhỉ?",
    "Bất cứ điều gì bạn cần, mình luôn sẵn sàng giúp đỡ bạn!",
]
GOODBYE_MESSAGE = "Tạm biệt bạn nhé, hẹn gặp lại vào một ngày không xa!"

# Khởi tạo PyAudio ở Global để dùng chung cho toàn bộ chương trình
p = pyaudio.PyAudio()
stream_player = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE_TTS, output=True)



def stt(audio_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='vi-VN')
            print(f"👤 Bạn nói: {text}")
            return text
    except Exception:
        robot_speak("Xin lỗi, tôi không nghe rõ bạn nói gì.")
        return None

# Hàm kiểm tra và trả lời câu hỏi về thời gian
async def time_answer(text):
    t = text.lower()
    now = datetime.datetime.now()
    d = now.day
    m = now.month
    y = now.year
    h = now.hour
    mi = now.minute
    s = now.second
    if "mấy giờ" in t or "bây giờ là mấy giờ" in t:
        return f"Bây giờ là {h} giờ {mi} phút { s} giây."
    if "ngày" in t or "hôm nay là ngày" in t:
        return f"Hôm nay là ngày {d} tháng {m} năm {y}."
    return None

# Hàm xử lý trao đổi văn bản qua WebSocket
async def handle_text_io(websocket, text_input):
    try:

        # ===== ƯU TIÊN LOCAL TIME =====
        local_time = await time_answer(text_input)
        if local_time:
            print(f"🤖 Robot: {local_time}")

            url = f"{STREAM_URL}?text={quote(local_time)}"
            start_time = time.perf_counter()
            first_chunk = True

            with requests.get(url, stream=True, timeout=20) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=2048):
                    if chunk:
                        if first_chunk:
                            latency = time.perf_counter() - start_time
                            print(f"Phát tiếng sau: {latency:.2f}s")
                            stream_player.write(chunk[44:])
                            first_chunk = False
                        else:
                            stream_player.write(chunk)

            return

        await websocket.send(text_input)

        response = await websocket.recv()

        if isinstance(response, str):
            print(f" Robot: {response}")

            url = f"{STREAM_URL}?text={quote(response)}"
            start_time = time.perf_counter()
            first_chunk = True

            with requests.get(url, stream=True, timeout=20) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=2048):
                    if chunk:
                        if first_chunk:
                            latency = time.perf_counter() - start_time
                            print(f" Phát tiếng sau: {latency:.2f}s")
                            stream_player.write(chunk[44:])
                            first_chunk = False
                        else:
                            stream_player.write(chunk)

    except Exception as e:
        print(f" Lỗi trao đổi: {e}")

# Hàm setup robot nói bị động
def robot_speak(text):
    print(f"Robot: {text}")

    url = f"{STREAM_URL}?text={quote(text)}"
    start_time = time.perf_counter()
    first_chunk = True

    with requests.get(url, stream=True, timeout=20) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=2048):
            if chunk:
                if first_chunk:
                    latency = time.perf_counter() - start_time
                    stream_player.write(chunk[44:])  # bỏ header wav
                    first_chunk = False
                else:
                    stream_player.write(chunk)

    print("--- Robot nói xong ---")

# Hàm vòng lặp chính
async def voice_loop():
    print(" Robot sẵn sàng (No-Pop Mode)!")
    try:
        async with websockets.connect(TTS_URI) as websocket:
            print(f"Đã kết nối tới: {TTS_URI}")
            robot_speak(random.choice(HELLO_MESSAGES))
            while True:
                filename = record()

                # ===== KHÔNG CÓ GIỌNG =====
                if filename == "__NO_VOICE__":
                    robot_speak(random.choice(FEEDBACK_MESSAGE))
                    await asyncio.sleep(1.0)
                    continue

                if not filename:
                    continue

                text_input = stt(filename)
                if not text_input: continue
                
                await handle_text_io(websocket, text_input)
                await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        robot_speak(GOODBYE_MESSAGE)
        time.sleep(0.5)

    except Exception as e:
        print(f"Lỗi kết nối: {e}")

    finally:
        # CHỈ ĐÓNG KHI TẮT HẲN CHƯƠNG TRÌNH
        print("Đã đóng chương trình.")
        stream_player.stop_stream()
        stream_player.close()
        p.terminate()

if __name__ == "__main__":
    asyncio.run(voice_loop())