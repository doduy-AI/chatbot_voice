import numpy as np, sounddevice as sd
data = open("server_sent_audio.raw", "rb").read()
audio = np.frombuffer(data, dtype=np.int16)
sd.play(audio, 24000)
sd.wait()
