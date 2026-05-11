import speech_recognition as sr

def capture_audio():
    # modulo hardware que captura la entrada de audio del entorno
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        # calibramos un segundo completo para evitar falsos positivos de ruido
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            # graba bloques de audio y se detiene si hay silencio
            audio_data = recognizer.listen(source, timeout=None, phrase_time_limit=10)
            return audio_data
        except Exception:
            return None