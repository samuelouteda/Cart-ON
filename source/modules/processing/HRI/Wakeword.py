import os
import json
import pyaudio
import numpy as np
from vosk import Model, KaldiRecognizer

class WakeWordDetector:
    def __init__(self, wake_word="carton"):
        directorio = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(directorio, "model")

        self.wake_word = wake_word

        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)

        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )
        self.stream.start_stream()

    def listen(self):
        data = self.stream.read(4000, exception_on_overflow=False)

        if self.recognizer.AcceptWaveform(data):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").lower()

            if self.wake_word in text:
                return True

        return False
