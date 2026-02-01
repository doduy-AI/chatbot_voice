import sounddevice as sd
import numpy as np
import wave
import time
import webrtcvad
import ctypes
import samplerate
from scipy.signal import butter, lfilter

# ================= CONFIG =================
INPUT_SR = 16000
RNNOISE_SR = 48000

FRAME_MS = 10
FRAME_16K = int(INPUT_SR * FRAME_MS / 1000)      # 160
FRAME_48K = int(RNNOISE_SR * FRAME_MS / 1000)    # 480

MAX_RECORD_TIME = 15.0
SILENCE_TIMEOUT = 3.0
VAD_MODE = 2

# ---- anti-noise / anti-music ----
MIN_SPEECH_FRAMES = 20      # 200ms
ENERGY_RATIO = 1.4
RMS_DELTA_MIN = 0.0002
NOISE_ALPHA = 0.95  

ZCR_MIN = 0.02
SPEECH_BAND_RATIO = 0.45

DOM_WINDOW = 30      # 300ms
DOM_THRESHOLD = 0.4  # chỉ cần 40% là giọng người

OUTPUT_WAV = "voice.wav"
# ========================================

# -------- RNNoise --------
rnnoise = ctypes.cdll.LoadLibrary("librnnoise.so")
rnnoise.rnnoise_process_frame.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
]
rnnoise.rnnoise_create.restype = ctypes.c_void_p
rnnoise_state = rnnoise.rnnoise_create(None)

# -------- WebRTC VAD --------
vad = webrtcvad.Vad(VAD_MODE)

# -------- Filters --------
def highpass(x, cutoff=80):
    b, a = butter(1, cutoff / (INPUT_SR / 2), btype='high')
    return lfilter(b, a, x)

# -------- Resamplers --------
to_48k = samplerate.Resampler('sinc_fastest', channels=1)
to_16k = samplerate.Resampler('sinc_fastest', channels=1)

def zero_crossing_rate(x):
    return np.mean(np.abs(np.diff(np.sign(x)))) / 2

def speech_band_ratio(x):
    fft = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1 / INPUT_SR)

    speech_energy = np.sum(
        fft[(freqs > 300) & (freqs < 3400)]
    )
    total_energy = np.sum(fft) + 1e-9

    return speech_energy / total_energy

# -------- Main --------
def record():
    print("🎙️  Bắt đầu nghe...")

    frames = []
    start_time = time.time()
    last_voice = time.time()

    speech_frames = 0
    noise_floor = 0.001
    prev_rms = 0.0

    with sd.InputStream(
        samplerate=INPUT_SR,
        channels=1,
        blocksize=FRAME_16K,
        dtype='float32'
    ) as stream:
        dom_buf = []

        while True:
            audio, _ = stream.read(FRAME_16K)
            audio = highpass(audio[:, 0])

            # --- 16k → 48k ---
            audio_48k = to_48k.process(audio, RNNOISE_SR / INPUT_SR)
            if len(audio_48k) != FRAME_48K:
                continue

            # --- RNNoise ---
            in_buf = (ctypes.c_float * FRAME_48K)(*audio_48k)
            out_buf = (ctypes.c_float * FRAME_48K)()
            rnnoise.rnnoise_process_frame(rnnoise_state, out_buf, in_buf)
            clean_48k = np.frombuffer(out_buf, dtype=np.float32)

            # --- 48k → 16k ---
            clean_16k = to_16k.process(clean_48k, INPUT_SR / RNNOISE_SR)
            if len(clean_16k) != FRAME_16K:
                continue

            # ---- save audio ----
            pcm16 = (clean_16k * 32768).astype(np.int16).tobytes()
            frames.append(pcm16)

            # ---- VAD ----
            is_speech = vad.is_speech(pcm16, INPUT_SR)

            # ---- RMS + delta (anti music) ----
            rms = np.sqrt(np.mean(clean_16k ** 2) + 1e-9)
            rms_delta = abs(rms - prev_rms)
            prev_rms = rms

            # ---- update noise floor ----
            if not is_speech:
                noise_floor = NOISE_ALPHA * noise_floor + (1 - NOISE_ALPHA) * rms

            # ---- speech confirmation ----
            zcr = zero_crossing_rate(clean_16k)
            band_ratio = speech_band_ratio(clean_16k)

            speech_candidate = (
                is_speech and
                rms > noise_floor * ENERGY_RATIO and
                rms_delta > RMS_DELTA_MIN and
                zcr > ZCR_MIN and
                band_ratio > SPEECH_BAND_RATIO
            )


            if speech_candidate:
                speech_frames += 1
            else:
                speech_frames = max(0, speech_frames - 1)

            dom_buf.append(1 if speech_candidate else 0)
            if len(dom_buf) > DOM_WINDOW:
                dom_buf.pop(0)

            dominance = sum(dom_buf) / len(dom_buf)

            # ---- ONLY human voice resets timer ----
            # if speech_frames >= MIN_SPEECH_FRAMES:
            #     last_voice = time.time()
            #     print("🗣️  HUMAN VOICE     ", end="\r")
            # else:
            #     print("🎵  NOISE / MUSIC  ", end="\r")
            if dominance > DOM_THRESHOLD:
                last_voice = time.time()
                print("🗣️  HUMAN VOICE", end="\r")
            else:
                print("🔇  NO VOICE   ", end="\r")

            # ---- stop conditions ----
            now = time.time()
            if now - last_voice > SILENCE_TIMEOUT:
                print("\n⏹️  Không có giọng người 3s → dừng")
                break

            if now - start_time > MAX_RECORD_TIME:
                print("\n⏹️  Đủ 15s → dừng")
                break

    # ---- Save WAV ----
    with wave.open(OUTPUT_WAV, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(INPUT_SR)
        wf.writeframes(b"".join(frames))

    print(f"✅ Đã lưu file: {OUTPUT_WAV}")
    return OUTPUT_WAV

