import sys
from pathlib import Path
import requests
import base64
import time
import json
import io  # Para generar la imagen falsa si hace falta

# --- HACK PARA ENCONTRAR LA CARPETA 'CORE' ---
current_dir = Path(__file__).resolve().parent
source_dir = current_dir.parent.parent.parent
sys.path.append(str(source_dir))
# ---------------------------------------------

from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

# Librerías nativas para las pantallas en Raspberry Pi 4
from PIL import Image, ImageDraw

try:
    from luma.core.interface.serial import spi
    from luma.oled.device import sh1106
    LUMA_AVAILABLE = True
except ImportError:
    LUMA_AVAILABLE = False
    print("⚠️ [HRI] Librería 'luma' no encontrada. Ejecutando en modo sin pantallas (PC).")

class HRI(BaseModule):
    """
    Layer 2: HRI Module (CLIENTE LIGERO). 
    Controla el hardware local (micrófono, pantallas) y delega el pensamiento a la nube.
    """

    def __init__(self, name, event_bus, shared_sensor_stream, stt_tts_api_key):
        super().__init__(name, event_bus)
        self.data_stream = shared_sensor_stream
        self.api_key = stt_tts_api_key
        
        # ☁️ URL DEL CEREBRO EN LA NUBE (Google Cloud Run)
        self.cloud_brain_url = "https://cart-on-api-225606614592.europe-southwest1.run.app/api/v1/interaccion"
        print(f"[{self.name}] Módulo ligero iniciado. Conectado a la nube en: {self.cloud_brain_url}")
        
        # --- CONFIGURACIÓN HARDWARE SPI (Pantallas) ---
        if LUMA_AVAILABLE:
            try:
                self.serial_izq = spi(device=0, port=0, gpio_DC=24, gpio_RST=25)
                self.serial_der = spi(device=1, port=0, gpio_DC=24, gpio_RST=25)
                self.ojo_izq = sh1106(self.serial_izq, width=128, height=64)
                self.ojo_der = sh1106(self.serial_der, width=128, height=64)
            except Exception as e:
                print(f"[{self.name}] ERROR iniciando pantallas físicas: {e}")
                self.ojo_izq = None
                self.ojo_der = None
        else:
            self.ojo_izq = None
            self.ojo_der = None

        # --- ESTADO EMOCIONAL ---
        self.emocion_actual = "neutral"
        self.ultimo_cambio_emocion = time.time()

    def get_audio(self): return self.data_stream['audio']
    
    def consume_audio(self): self.data_stream['audio'] = None
    
    def read_audio(self):
        audio = self.data_stream['audio']
        self.consume_audio()
        return audio

    # 🚀 LA CONEXIÓN CLOUD: Empaqueta la solicitud y se la manda a Google Cloud Run
    def query_cloud_brain(self, raw_text):
        print(f"[{self.name}] ☁️ Enviando petición al servidor central...")
        data_payload = {"frase_usuario": raw_text}
        
        frame_bytes = self.data_stream.get('frame')
        if frame_bytes:
            files_payload = {"image_file": ("frame.jpg", frame_bytes, "image/jpeg")}
        else:
            # 🖼️ EL PARCHE: Creamos un mini cuadrado negro para que la UAB no se queje
            img = Image.new('RGB', (10, 10), color='black')
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG')
            files_payload = {"image_file": ("dummy.jpg", img_io.getvalue(), "image/jpeg")}
            
        try:
            response = requests.post(self.cloud_brain_url, data=data_payload, files=files_payload)
            response.raise_for_status()
            
            datos = response.json()
            print(f"[{self.name}] 🧠 Respuesta de la Nube: {datos}")
            
            return (
                datos.get("intent", "unknown"),
                datos.get("producto_detectado", None),
                1, 
                datos.get("texto", None)
            )
        except Exception as e:
            print(f"[{self.name}] 🔴 Error conectando al Cerebro Cloud: {e}")
            return "unknown", None, 1, "He perdido la conexión con mis servidores centrales."

    # Mantenemos STT y TTS porque usan la API directa (es ligero para la Raspberry)
    def speech_to_text(self, audio_data):
        audio_wav = audio_data.get_wav_data()
        audio_b64 = base64.b64encode(audio_wav).decode("utf-8")
        endpoint_url = f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}"
        payload = {
            "config": {"encoding": "LINEAR16", "sampleRateHertz": audio_data.sample_rate, "languageCode": "es-ES"},
            "audio": {"content": audio_b64}
        }
        try:
            response = requests.post(endpoint_url, json=payload)
            if "results" in response.json(): return response.json()["results"][0]["alternatives"][0]["transcript"].lower().strip()
        except Exception as e: print(f"SST Connection error: {e}")
        return None
    
    def text_to_speech(self, text_to_say):
        endpoint_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
        payload = {
            "input": {"text": text_to_say},
            "voice": {"languageCode": "es-ES", "name": "es-ES-Neural2-F"},
            "audioConfig": {"audioEncoding": "MP3"}
        }
        try:
            response = requests.post(endpoint_url, json=payload)
            if "audioContent" in response.json(): return base64.b64decode(response.json()["audioContent"])
        except Exception as e: print(f"TTS Petition error: {e}")
        return None
    
    def set_emocion(self, nueva_emocion):
        if nueva_emocion != self.emocion_actual:
            self.emocion_actual = nueva_emocion
            self.ultimo_cambio_emocion = time.time()

    def renderizar_ojos(self):
        if not self.ojo_izq or not self.ojo_der: return 
        canvas_izq = Image.new("1", (128, 64))
        canvas_der = Image.new("1", (128, 64))
        draw_izq = ImageDraw.Draw(canvas_izq)
        draw_der = ImageDraw.Draw(canvas_der)

        if self.emocion_actual == "neutral":
            draw_izq.rectangle([34, 24, 94, 40], fill="white")
            draw_der.rectangle([34, 24, 94, 40], fill="white")
        elif self.emocion_actual == "feliz":
            draw_izq.chord([34, 20, 94, 50], start=180, end=360, fill="white")
            draw_der.chord([34, 20, 94, 50], start=180, end=360, fill="white")
        elif self.emocion_actual == "confuso":
            draw_izq.ellipse([44, 12, 84, 52], fill="white")
            draw_der.rectangle([34, 28, 94, 36], fill="white")
        elif self.emocion_actual == "enfadado":
            draw_izq.rectangle([34, 24, 94, 40], fill="white")
            draw_der.rectangle([34, 24, 94, 40], fill="white")
            draw_izq.polygon([34, 24, 94, 24, 94, 32], fill="black")
            draw_der.polygon([34, 24, 94, 24, 34, 32], fill="black")

        self.ojo_izq.display(canvas_izq)
        self.ojo_der.display(canvas_der)

    def process_audio(self):
        audio_data = self.read_audio()
        if not audio_data: return

        print(f"{INDENT_OUTPUT}[{self.name}] Escuchando...")
        raw_text = self.speech_to_text(audio_data)
        if not raw_text: return
        
        print(f"{INDENT_OUTPUT}[{self.name}] Usuario dice: \"{raw_text}\"")
        
        # 🔄 Disparamos a la NUBE en lugar de usar procesamiento local
        intent, item, quantity, reply = self.query_cloud_brain(raw_text)

        if intent == "chat" and reply:
            print(f"{INDENT_OUTPUT}[{self.name}] Charla detectada. Respondiendo...")
            self.set_emocion("feliz")
            self.speak(reply)
            return

        elif intent == "unknown":
            print(f"{INDENT_OUTPUT}[{self.name}] Orden desconocida o error en la nube.")
            self.set_emocion("confuso")
            self.speak(reply if reply else "No te he entendido bien.")
            return
    
        else:
            self.publish_event(
                Event(
                    type="voice_command", 
                    data={"intent": intent, "item": item, "quantity": quantity, "raw_text": raw_text}, 
                    origin=self.name
                )
            )

    def handle_task(self, task):
        if task.type == "speak": print(f"    [{self.name}] Playing audio.")
        elif task.type == "set_emotion": self.set_emocion(task.data.get("emotion", "neutral"))

    def speak(self, text):
        print(f"{INDENT_OUTPUT}[{self.name}] Robot: {text}")
        audio_bytes = self.text_to_speech(text)

    def loop(self):
        self.process_audio()
        self.renderizar_ojos() 
        
        if self.emocion_actual != "neutral" and time.time() - self.ultimo_cambio_emocion > 4.0:
            self.set_emocion("neutral")

# =======================================================================================
# ZONA DE TEST
# =======================================================================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" ☁️ INICIANDO TEST DEL CLIENTE LIGERO HRI ☁️")
    print("="*50)

    class MockEventBus:
        def put(self, event):
            print(f"\n 📬 [BUS FALSO] El HRI intentó publicar un evento:")
            print(f"      Tipo: {event.type}")
            print(f"      Datos: {event.data}")

    mock_bus = MockEventBus()
    mock_stream = {"audio": None, "frame": None}

    # Tu clave original de Google Cloud para el Speech-to-Text
    API_KEY_GOOGLE = "AIzaSyCMV4L39MGvadx6XLsm_99Comj4sZ5EUn4"

    print("\n[!] Encendiendo el módulo HRI (Cliente)...")
    hri_test = HRI(
        name="HRI_Test",
        event_bus=mock_bus,
        shared_sensor_stream=mock_stream,
        stt_tts_api_key=API_KEY_GOOGLE
    )

    print("\n--- PRUEBA DE CONEXIÓN CON TU NUBE DE GOOGLE RUN ---")
    
    frases_prueba = [
        "¿Cuánto cuesta apple?",
        "Hola maquinita, ¿qué tal estás hoy?"
    ]

    for frase in frases_prueba:
        print(f"\n🗣️ Humano dice: '{frase}'")
        intent, item, quantity, reply = hri_test.query_cloud_brain(frase)
        
        print(f"🤖 Tu servidor en Madrid devuelve:")
        print(f"   - Intención : {intent}")
        print(f"   - Producto  : {item}")
        print(f"   - Cantidad  : {quantity}")
        print(f"   - Respuesta : {reply}")

    print("\n" + "="*50)
    print(" TEST FINALIZADO.")
    print("="*50)