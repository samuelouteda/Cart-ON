from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

import requests
import base64
import time

# Librerías nativas para las pantallas en Raspberry Pi 4
from luma.core.interface.serial import spi
from luma.oled.device import sh1106  # Cambia a ssd1306 si tus pantallas usan ese chip
from PIL import Image, ImageDraw

class HRI(BaseModule):
    """
    Layer 2: Human-Robot Interaction Module para Raspberry Pi 4 (SPI)
    """

    _add_commands = ["añadir", "añade", "añádeme", "mete", "apunta", "pon"]
    _delete_commands = ["borrar", "borra", "quita", "elimina", "saca"]
    _read_commands = ["qué hay", "lee", "dime", "cuál es", "revisa", "muestra", "enseña"]
    _clear_commands = ["vaciar", "vacía", "limpia", "borra toda"]

    _filler_words = ["por", "favor", "porfa", "a", "en", "la", "lista", "quiero", "necesito", "el", "los", "las", "un", "una"]
    _containers = ["bote", "botes", "pote", "potes", "litro", "litros", "paquete", "paquetes", "botella", "botellas", "de"]

    _number_mapping = {
        "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, 
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10
    }

    def __init__(self, name, event_bus, shared_sensor_stream, api_key):
        super().__init__(name, event_bus)
        self.data_stream = shared_sensor_stream
        self.api_key = api_key
        
        # --- CONFIGURACIÓN HARDWARE SPI (Raspberry Pi 4) ---
        # Comparten SPI bus 0, Reset y DC. Cada pantalla tiene su propio pin CE (Chip Enable)
        # Ojo Izquierdo en CE0 (GPIO 8), Ojo Derecho en CE1 (GPIO 7)
        try:
            self.serial_izq = spi(device=0, port=0, gpio_DC=24, gpio_RST=25)
            self.serial_der = spi(device=1, port=0, gpio_DC=24, gpio_RST=25)
            
            # Inicializamos los dispositivos (SH1106 es el estándar de 1.3")
            self.ojo_izq = sh1106(self.serial_izq, width=128, height=64)
            self.ojo_der = sh1106(self.serial_der, width=128, height=64)
        except Exception as e:
            print(f"[{self.name}] ERROR iniciando pantallas físicas: {e}")
            print(f"[{self.name}] Modo simulación virtual activado (Cuidado en producción).")
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

    def extract_quantity_and_product(self, spoken_text, command_list):
        for command in command_list: spoken_text = spoken_text.replace(command, "")
        words = spoken_text.split()
        quantity = 1 
        product_words = []
        for word in words:
            if word.isdigit(): quantity = int(word)
            elif word in self._number_mapping: quantity = self._number_mapping[word]
            elif word not in self._filler_words and word not in self._containers: product_words.append(word)
        return quantity, " ".join(product_words).strip()

    def parse_intent(self, raw_text):
        if any(command in raw_text for command in self._add_commands):
            quantity, item = self.extract_quantity_and_product(raw_text, self._add_commands)
            return "add", item, quantity
        elif any(command in raw_text for command in self._delete_commands):
            quantity, item = self.extract_quantity_and_product(raw_text, self._delete_commands)
            return "delete", item, quantity
        elif any(command in raw_text for command in self._read_commands): return "read", None, None
        elif any(command in raw_text for command in self._clear_commands): return "clear", None, None
        return "unknown", None, None

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
            response_json = response.json()
            if "results" in response_json: return response_json["results"][0]["alternatives"][0]["transcript"].lower().strip()
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
            response_json = response.json()
            if "audioContent" in response_json: return base64.b64decode(response_json["audioContent"])
        except Exception as e: print(f"TTS Petition error: {e}")
        return None
    
    # --- PROCESADOR GRÁFICO (Inspirado en roboeyes del repositorio) ---
    def set_emocion(self, nueva_emocion):
        if nueva_emocion != self.emocion_actual:
            self.emocion_actual = nueva_emocion
            self.ultimo_cambio_emocion = time.time()

    def renderizar_ojos(self):
        """Dibuja los frames usando Pillow siguiendo las pautas de roboeyes"""
        if not self.ojo_izq or not self.ojo_der:
            return # Evita crasheos si no hay pantallas conectadas testeando en PC

        # Creamos dos lienzos en blanco independientes (128x64)
        canvas_izq = Image.new("1", (128, 64))
        canvas_der = Image.new("1", (128, 64))
        
        draw_izq = ImageDraw.Draw(canvas_izq)
        draw_der = ImageDraw.Draw(canvas_der)

        if self.emocion_actual == "neutral":
            # Ojos rectangulares centrados estilo Cozmo
            draw_izq.rectangle([34, 24, 94, 40], fill="white")
            draw_der.rectangle([34, 24, 94, 40], fill="white")
            
        elif self.emocion_actual == "feliz":
            # Ojos arqueados en forma de U invertida (Pillows utiliza arcos/polígonos)
            draw_izq.chord([34, 20, 94, 50], start=180, end=360, fill="white")
            draw_der.chord([34, 20, 94, 50], start=180, end=360, fill="white")
            
        elif self.emocion_actual == "confuso":
            # Asimetría: Ojo izquierdo circular grande, derecho una línea neutra
            draw_izq.ellipse([44, 12, 84, 52], fill="white")
            draw_der.rectangle([34, 28, 94, 36], fill="white")
            
        elif self.emocion_actual == "enfadado":
            # Líneas diagonales agresivas recortando la parte superior interna
            draw_izq.rectangle([34, 24, 94, 40], fill="white")
            draw_der.rectangle([34, 24, 94, 40], fill="white")
            # Ceño fruncido tapando con rectángulos negros inclinados
            draw_izq.polygon([34, 24, 94, 24, 94, 32], fill="black")
            draw_der.polygon([34, 24, 94, 24, 34, 32], fill="black")

        # Enviamos los datos binarios directamente al hardware SPI de las pantallas
        self.ojo_izq.display(canvas_izq)
        self.ojo_der.display(canvas_der)

    def process_audio(self):
        audio_data = self.read_audio()
        if not audio_data: return

        print(f"{INDENT_OUTPUT}[{self.name}] Listening...")
        raw_text = self.speech_to_text(audio_data)
        if not raw_text: return
        
        print(f"{INDENT_OUTPUT}[{self.name}] Audio detected: \"{raw_text}\"")
        intent, item, quantity = self.parse_intent(raw_text)

        if intent == "unknown":
            print(f"{INDENT_OUTPUT}[{self.name}] Unknown order. Ignoring input.")
            self.set_emocion("confuso")
            return
    
        self.publish_event(
            Event(type="voice_command", data={"intent": intent, "item": item, "quantity": quantity, "raw_text": raw_text}, origin=self.name)
        )

    def handle_task(self, task):
        if task.type == "speak": print(f"    [{self.name}] Playing audio.")
        elif task.type == "set_emotion": self.set_emocion(task.data.get("emotion", "neutral"))

    def speak(self, text):
        print(f"{INDENT_OUTPUT}[{self.name}] Robot: {text}")
        audio_bytes = self.text_to_speech(text, self.api_key)

    def loop(self):
        self.process_audio()
        self.renderizar_ojos() # Refresca las pantallas físicas en cada ciclo
        
        # Volver al estado normal tras 4 segundos de emoción reactiva
        if self.emocion_actual != "neutral" and time.time() - self.ultimo_cambio_emocion > 4.0:
            self.set_emocion("neutral")