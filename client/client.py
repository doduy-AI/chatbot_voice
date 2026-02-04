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
import aiohttp

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
    "Chào bạn nha! tớ đã lên sóng, mình giúp gì được cho bạn đây?",
    "Hí! tớ đây, hôm nay bạn có chuyện gì vui không? Cần mình hỗ trợ gì nói nhé!",
    "Hê Nhô! Rất vui được gặp lại bạn, mình cùng bắt đầu thôi nào.",
    "tớ có mặt! Bạn cần mình tư vấn hay giúp đỡ việc gì không nhỉ?",
    "Chào bạn nha, mình đang lắng nghe đây, cứ nói thoải mái nhé!",
    "Ting ting! tớ đã sẵn sàng, bạn muốn hỏi gì mình cũng được nè.",
    "Hêy ! Hôm nay của bạn thế nào? Cần tớ giúp một tay không?",
    "Chào bạn, mình chờ nãy giờ luôn á! Cùng làm việc thôi nào.",
    "Chào bạn nhé! tớ rất hân hạnh được đồng hành cùng bạn hôm nay."
]

FEEDBACK_MESSAGE = [
    "Ơ kìa, mình chưa nghe rõ bạn nói gì hết, bạn nói lại lần nữa được không?",
    "Hình như chỗ bạn hơi ồn hoặc micro có vấn đề rồi, mình không nghe thấy gì cả.",
    "Bạn ơi, bạn còn đó không? Nói gì đó với mình đi cho đỡ buồn nè!",
    "Tớ  chưa nghe rõ lắm, bạn nói chậm lại một chút với mình nha.",
    "Có vẻ bạn đang bận gì à? Khi nào cần thì cứ gọi tớ nhé!",
    "Mình vẫn đang đợi bạn nè, có chuyện gì cần mình giải đáp không?"
]

GOODBYE_MESSAGE = "Hẹn gặp lại bạn sớm nha, tớ luôn ở đây chờ bạn đó. Tạm biệt!"
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
        # local_time = await time_answer(text_input)
        # if local_time:
        #     print(f"🤖 Robot: {local_time}")

        #     url = f"{STREAM_URL}?text={quote(local_time)}"
        #     start_time = time.perf_counter()
        #     first_chunk = True

        #     with requests.get(url, stream=True, timeout=20) as r:
        #         r.raise_for_status()
        #         for chunk in r.iter_content(chunk_size=2048):
        #             if chunk:
        #                 if first_chunk:
        #                     latency = time.perf_counter() - start_time
        #                     print(f"Phát tiếng sau: {latency:.2f}s")
        #                     stream_player.write(chunk[44:])
        #                     first_chunk = False
        #                 else:
        #                     stream_player.write(chunk)

        #     return

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
async def robot_speak(text): # Chuyển thành async def
    print(f"Robot: {text}")
    url = f"{STREAM_URL}?text={quote(text)}"
    start_time = asyncio.get_event_loop().time()
    first_chunk = True

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as r:
                r.raise_for_status()
                async for chunk in r.content.iter_chunked(2048):
                    if chunk:
                        if first_chunk:
                            latency = asyncio.get_event_loop().time() - start_time
                            print(latency)
                            stream_player.write(chunk[44:])  
                            first_chunk = False
                        else:
                            stream_player.write(chunk)
                        await asyncio.sleep(0) 

        print("--- Robot nói xong ---")
    except Exception as e:
        print(f"Lỗi khi phát âm thanh: {e}")
# Hàm vòng lặp chính
async def voice_loop():
    print(" Robot sẵn sàng (No-Pop Mode)!")
    try:
        async with websockets.connect(TTS_URI) as websocket:
            print(f"Đã kết nối tới: {TTS_URI}")
            await robot_speak(random.choice(HELLO_MESSAGES))
            while True:
                filename = record()

                # ===== KHÔNG CÓ GIỌNG =====
                if filename == "__NO_VOICE__":
                    await robot_speak(random.choice(FEEDBACK_MESSAGE))
                    await asyncio.sleep(1.0)
                    continue

                if not filename:
                    continue

                text_input = stt(filename)
                if not text_input: continue
                
                await handle_text_io(websocket, text_input)
                await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        await robot_speak(GOODBYE_MESSAGE)
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