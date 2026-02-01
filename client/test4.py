from vieneu import FastVieNeuTTS
import numpy as np
from scipy.io.wavfile import write

tts = FastVieNeuTTS(
    backbone_repo="pnnbao-ump/VieNeu-TTS",   # hoặc thử bản 0.5B nếu có
    backbone_device="cuda",
    codec_repo="neuphonic/distill-neucodec",
    codec_device="cuda",
    enable_triton=True,
    enable_prefix_caching=False
)

# ✅ Lấy danh sách voices từ hàm nội bộ
voices = tts._load_voices()
print(f"🎤 Có {len(voices)} giọng trong model:")
for v in voices:
    print(f" - {v['name']} ({v.get('gender', 'unknown')})")

# Chọn giọng đầu tiên làm mặc định
default_voice_name = voices[0]["name"]
print(f"👉 Dùng giọng mặc định: {default_voice_name}")

voice = tts.get_preset_voice(default_voice_name)

text = "Xin chào, mình là robot VieNeu TTS! Hôm nay chúng ta cùng nói chuyện nhé."
audio_chunks = []

print("--- Bắt đầu sinh âm thanh ---")
for chunk in tts.infer_stream(text, voice=voice, temperature=1.0):
    print(f"Chunk size: {len(chunk)}")
    audio_chunks.append(chunk)

if len(audio_chunks) == 0:
    print("❌ Không sinh ra bất kỳ chunk nào. Có thể model gặp lỗi.")
else:
    audio = np.concatenate(audio_chunks)
    print(f"✅ Tổng mẫu: {len(audio)} ({len(audio)/24000:.2f} giây)")
    write("test_output.wav", 24000, (audio * 32767).astype(np.int16))
    print("💾 Đã lưu file test_output.wav — bạn có thể tải về và nghe thử.")
