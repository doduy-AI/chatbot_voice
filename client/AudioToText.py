import sys
import speech_recognition as sr

# Cần ít nhất 3 tham số: file audio + lang
if len(sys.argv) < 3:
    print("Thiếu tham số. Dùng: python3 stt.py <file.wav> <vi-VN|en-US>")
    sys.exit(1)

audio_path = sys.argv[1]
lang_code = sys.argv[2] 

r = sr.Recognizer()

with sr.AudioFile(audio_path) as source:
    audio = r.record(source)

try:
    text = r.recognize_google(audio, language="vi")
    print(text)
except Exception as e:
    print(f"Lỗi: {e}")
