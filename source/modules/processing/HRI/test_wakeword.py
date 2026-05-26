import os
import sys
import json
import pyaudio
import numpy as np
from vosk import Model, KaldiRecognizer, SetLogLevel

def test_vosk_wakeword():
    #elrichmc 2024-06-20
    # 1. Verificar que la carpeta del modelo existe
    directorio_script = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Construimos la ruta pegando "model" a ese directorio
    model_path = os.path.join(directorio_script, "model")
    
    if not os.path.exists(model_path):
        print(f"Error: No encuentro la carpeta '{model_path}'.")
        print("Descarga el modelo 'vosk-model-small-es', descomprímelo y llámalo 'model'.")
        sys.exit(1)

    print("Cargando cerebro de Vosk en español (100% offline)...")
    
    modelo = Model(model_path)
    # 16000 Hz es la frecuencia estándar para estos modelos
    reconocedor = KaldiRecognizer(modelo, 16000)

    # 3. Configurar el Micrófono
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 4000 # Bloques de audio más grandes para Vosk
    
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    stream.start_stream()

    print("\n Cart-ON! Di 'carton' para despertar al robot.")

    try:
        while True:
            # Leer datos del micrófono
            data = stream.read(CHUNK, exception_on_overflow=False)
            
            # --- DEBUG DE HARDWARE (Volumen) ---
            audio_data = np.frombuffer(data, dtype=np.int16)
            volumen = np.max(np.abs(audio_data))
            
            # Imprimimos un indicador visual si hay ruido
            if volumen > 300:
                print(f"[Volumen: {volumen:5d}] Escuchando...", end="\r", flush=True)

            # --- PROCESAMIENTO VOSK ---
            # AcceptWaveform devuelve True cuando detecta que has hecho una pausa al hablar
            if reconocedor.AcceptWaveform(data):
                # Extraemos el texto en formato JSON
                resultado = json.loads(reconocedor.Result())
                texto_detectado = resultado.get("text", "")
                
                if texto_detectado:
                    # Limpiamos la línea de volumen y mostramos lo que ha entendido
                    print(" " * 50, end="\r") 
                    print(f"🗣️  He entendido: '{texto_detectado}'")
                    
                    # Comprobar la Wake Word
                    if "carton" in texto_detectado or "cartón" in texto_detectado:
                        print("\n🔔 ¡WAKE WORD 'CARTÓN' DETECTADA!\n")
                        # Aquí enviaríamos el evento al Planner para despertar al robot
                        
    except KeyboardInterrupt:
        print("\nApagando oídos...")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

if __name__ == '__main__':
    test_vosk_wakeword()