import requests
import pyaudio
import time
from urllib.parse import quote # Thêm cái này để xử lý tiếng Việt trên URL

# Cấu hình loa
p = pyaudio.PyAudio()
stream_player = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)

text = "Hi there! My name is Duy, and today I’m testing my AI voice system. I want to see how natural and expressive this voice can sound, especially when I speak with different emotions — like excitement, curiosity, or calmness. So, let’s take a deep breath and begin this test together."

# MÃ HÓA TEXT ĐỂ CHÈN VÀO URL
url = f"http://192.168.1.35:8001/stream?text={quote(text)}"

print("--- Đang kết nối và chờ âm thanh... ---")
start_time = time.perf_counter()
first_chunk = True 

try:
    # Tăng timeout lên một chút vì câu này khá dài
    with requests.get(url, stream=True, timeout=20) as r:
        r.raise_for_status() # Kiểm tra xem server có trả về lỗi 404 hay 500 không
        
        for chunk in r.iter_content(chunk_size=2048): # Tăng chunk_size lên chút cho mượt
            if chunk:
                if first_chunk:
                    latency = time.perf_counter() - start_time
                    print(f"✅ Đã nhận âm thanh đầu tiên sau: {latency:.2f} giây")
                    first_chunk = False
                
                stream_player.write(chunk) 

except Exception as e:
    print(f"Lỗi: {e}")

print("--- Kết thúc phát âm thanh ---")

# Dọn dẹp để không bị treo card âm thanh
stream_player.stop_stream()
stream_player.close()
p.terminate()