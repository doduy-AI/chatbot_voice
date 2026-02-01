import asyncio
import websockets
import numpy as np
import sounddevice as sd
import wave
import time
import webrtcvad
import ctypes
import samplerate
from scipy.signal import butter, lfilter
import speech_recognition as sr

# ================= CONFIG (STT & AUDIO) =================
INPUT_SR = 16000
RNNOISE_SR = 48000
SAMPLE_RATE_TTS = 24000
FRAME_MS = 10
FRAME_16K = int(INPUT_SR * FRAME_MS / 1000)
FRAME_48K = int(RNNOISE_SR * FRAME_MS / 1000)

MAX_RECORD_TIME = 15.0
SILENCE_TIMEOUT = 2.5  # Rút ngắn chút cho robot phản hồi nhanh hơn
VAD_MODE = 2

# ---- Anti-noise config ----
ENERGY_RATIO = 1.4
RMS_DELTA_MIN = 0.0002
NOISE_ALPHA = 0.95  
ZCR_MIN = 0.02
SPEECH_BAND_RATIO = 0.45
DOM_WINDOW = 30      
DOM_THRESHOLD = 0.4  

OUTPUT_WAV = "input_voice.wav"
TTS_URI = "ws://127.0.0.1:6789/api/v1/tts/ws/doduy001"

# ================= INITIALIZE TOOLS =================
# Load RNNoise
try:
    rnnoise = ctypes.cdll.LoadLibrary("librnnoise.so")
    rnnoise.rnnoise_process_frame.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)]
    rnnoise.rnnoise_create.restype = ctypes.c_void_p
    rnnoise_state = rnnoise.rnnoise_create(None)
except:
    print("⚠️ Không tìm thấy librnnoise.so. Vui lòng kiểm tra lại đường dẫn.")

vad = webrtcvad.Vad(VAD_MODE)
to_48k = samplerate.Resampler('sinc_fastest', channels=1)
to_16k = samplerate.Resampler('sinc_fastest', channels=1)

# ================= HELPER FUNCTIONS =================
def highpass(x, cutoff=80):
    b, a = butter(1, cutoff / (INPUT_SR / 2), btype='high')
    return lfilter(b, a, x)

def zero_crossing_rate(x):
    return np.mean(np.abs(np.diff(np.sign(x)))) / 2

def speech_band_ratio(x):
    fft = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1 / INPUT_SR)
    speech_energy = np.sum(fft[(freqs > 300) & (freqs < 3400)])
    total_energy = np.sum(fft) + 1e-9
    return speech_energy / total_energy

# ================= CORE LOGIC =================

def smart_record():
    """Ghi âm lọc nhiễu và tự dừng khi hết giọng người (từ STT.py)"""
    print("\n🎙️  Robot đang nghe...")
    frames = []
    start_time = time.time()
    last_voice = time.time()
    noise_floor = 0.001
    prev_rms = 0.0
    dom_buf = []

    with sd.InputStream(samplerate=INPUT_SR, channels=1, blocksize=FRAME_16K, dtype='float32') as stream:
        while True:
            audio, _ = stream.read(FRAME_16K)
            audio = highpass(audio[:, 0])

            # Resample & RNNoise
            audio_48k = to_48k.process(audio, RNNOISE_SR / INPUT_SR)
            if len(audio_48k) != FRAME_48K: continue
            
            in_buf = (ctypes.c_float * FRAME_48K)(*audio_48k)
            out_buf = (ctypes.c_float * FRAME_48K)()
            rnnoise.rnnoise_process_frame(rnnoise_state, out_buf, in_buf)
            clean_16k = to_16k.process(np.frombuffer(out_buf, dtype=np.float32), INPUT_SR / RNNOISE_SR)
            
            if len(clean_16k) != FRAME_16K: continue

            pcm16 = (clean_16k * 32768).astype(np.int16).tobytes()
            frames.append(pcm16)

            # Phân tích giọng nói
            is_speech = vad.is_speech(pcm16, INPUT_SR)
            rms = np.sqrt(np.mean(clean_16k ** 2) + 1e-9)
            rms_delta = abs(rms - prev_rms)
            prev_rms = rms

            if not is_speech:
                noise_floor = NOISE_ALPHA * noise_floor + (1 - NOISE_ALPHA) * rms

            speech_candidate = (is_speech and rms > noise_floor * ENERGY_RATIO and 
                               rms_delta > RMS_DELTA_MIN and zero_crossing_rate(clean_16k) > ZCR_MIN and 
                               speech_band_ratio(clean_16k) > SPEECH_BAND_RATIO)

            dom_buf.append(1 if speech_candidate else 0)
            if len(dom_buf) > DOM_WINDOW: dom_buf.pop(0)
            
            if (sum(dom_buf) / len(dom_buf)) > DOM_THRESHOLD:
                last_voice = time.time()
                print("🗣️  Đang ghi nhận giọng nói...", end="\r")

            now = time.time()
            if now - last_voice > SILENCE_TIMEOUT or now - start_time > MAX_RECORD_TIME:
                break

    with wave.open(OUTPUT_WAV, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(INPUT_SR)
        wf.writeframes(b"".join(frames))
    return OUTPUT_WAV

def stt_process(audio_path):
    """Chuyển đổi file âm thanh vừa ghi thành văn bản"""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='vi-VN')
            print(f"\n✅ Duy nói: {text}")
            return text
    except:
        print("\n🤔 Robot không nghe rõ, hãy thử lại.")
        return None

async def tts_speak(websocket, text):
    """Gửi text đến TTS server và phát âm thanh ra loa"""
    await websocket.send(text)
    print("🔊 Robot đang trả lời...")
    while True:
        response = await websocket.recv()
        if isinstance(response, str) and response == "END_OF_STREAM":
            print("🏁 Kết thúc câu thoại.\n")
            break
        elif not isinstance(response, str):
            chunk = np.frombuffer(response, dtype=np.int16)
            sd.play(chunk, SAMPLE_RATE_TTS)
            sd.wait()

async def main_loop():
    print("--- HỆ THỐNG ROBOT BẮT ĐẦU ---")
    try:
        async with websockets.connect(TTS_URI) as websocket:
            while True:
                audio_file = smart_record()
                text_input = stt_process(audio_file)
                
                if text_input:
                    await tts_speak(websocket, text_input)
                
                await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print("\nBye Duy!")
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")

if __name__ == "__main__":
    asyncio.run(main_loop())