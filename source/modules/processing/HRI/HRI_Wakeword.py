import os
import json
import pyaudio
import numpy as np
from vosk import Model, KaldiRecognizer

class HRI_WakeWord:
    """
    HRI minimalista que només escolta la wake-word.
    Quan la detecta, retorna True i el HRI antic continua el flux normal.
    """

    def __init__(self, wake_word="carton"):
        self.wake_word = wake_word.lower()

        # Ruta del model Vosk
        base = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base, "model")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"No s'ha trobat el model Vosk a: {model_path}"
            )

        # Carregar model
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)

        # Configurar micròfon
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )
        self.stream.start_stream()

        print("[WakeWord] Sistema de wake-word inicialitzat.")

    def listen(self):
        """
        Escolta contínuament fins que detecta la wake-word.
        Retorna True quan la detecta.
        """
        data = self.stream.read(4000, exception_on_overflow=False)

        # Processar amb Vosk
        if self.recognizer.AcceptWaveform(data):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "").lower()

            if text:
                print(f"[WakeWord] He entès: '{text}'")

                if self.wake_word in text:
                    print("[WakeWord] WAKE-WORD DETECTADA!")
                    return True

        return False

    def close(self):
        """Tanca el micròfon i allibera recursos."""
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
