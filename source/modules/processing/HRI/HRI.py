from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

import requests
import base64
import time
import json
import google.generativeai as genai

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
    Layer 2: Human-Robot Interaction Module para Raspberry Pi 4 (SPI) + NLP Gemini
    """

    def __init__(self, name, event_bus, shared_sensor_stream, stt_tts_api_key, gemini_api_key):
        super().__init__(name, event_bus)
        self.data_stream = shared_sensor_stream
        self.api_key = stt_tts_api_key
        
        # --- CONFIGURACIÓN DE GEMINI API ---
        print(f"[{self.name}] Inicializando motor NLP Gemini...")
        genai.configure(api_key=gemini_api_key)
        self.nlp_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # --- CONFIGURACIÓN HARDWARE SPI (Raspberry Pi 4) ---
        # Comparten SPI bus 0, Reset y DC. Cada pantalla tiene su propio pin CE (Chip Enable)
        # Ojo Izquierdo en CE0 (GPIO 8), Ojo Derecho en CE1 (GPIO 7)
        # --- CONFIGURACIÓN HARDWARE SPI ---
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

    def parse_intent(self, raw_text):
        """
        Envía el texto a Gemini. Extrae órdenes o genera respuestas conversacionales.
        """
        prompt = f"""
        Eres la IA de un amigable robot asistente de supermercado.
        Analiza la petición del usuario y extrae la intención final.
        
        Intenciones válidas: 
        - "add" (añadir producto)
        - "delete" (quitar/borrar producto)
        - "read" (leer qué hay en la lista)
        - "clear" (vaciar toda la lista)
        - "chat" (saludos, insultos, preguntas sobre ti o charla general)
        - "unknown" (ruido sin sentido)

        Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:
        {{"intent": "valor", "quantity": numero_entero, "item": "nombre_del_producto", "reply": "respuesta conversacional"}}
        
        Reglas estrictas:
        1. Si la intención es "chat", en el campo "reply" debes escribir una respuesta amigable, muy breve y natural en español (máximo 2 frases).
        2. Si la intención NO es "chat" (ej: es "add" o "delete"), el campo "reply" debe ser null.
        3. Si no hay un producto claro, "item" es null. Si no especifica cantidad, "quantity" es 1.

        Petición del usuario: "{raw_text}"
        """

        try:
            respuesta = self.nlp_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            
            datos = json.loads(respuesta.text)
            print(f"[{self.name}] Gemini entendió: {datos}")
            
            intent = datos.get("intent", "unknown")
            item = datos.get("item", None)
            reply = datos.get("reply", None)
            
            try:
                quantity = int(datos.get("quantity", 1))
            except (ValueError, TypeError):
                quantity = 1
                
            return intent, item, quantity, reply

        except Exception as e:
            print(f"[{self.name}] ERROR en Gemini NLP: {e}")
            return "unknown", None, None, None            

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
    
    # --- PROCESADOR GRÁFICO ---
    def set_emocion(self, nueva_emocion):
        if nueva_emocion != self.emocion_actual:
            self.emocion_actual = nueva_emocion
            self.ultimo_cambio_emocion = time.time()

    def renderizar_ojos(self):
        if not self.ojo_izq or not self.ojo_der:
            return 

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
        
        # Ahora recibimos también el 'reply' de Gemini
        intent, item, quantity, reply = self.parse_intent(raw_text)

        # --- 1. Lógica de Interacción Social (Chat) ---
        if intent == "chat" and reply:
            print(f"{INDENT_OUTPUT}[{self.name}] Charla detectada. Respondiendo...")
            self.set_emocion("feliz")
            self.speak(reply)
            return # Terminamos aquí, no hay que añadir nada a la lista de la compra

        # --- 2. Lógica de Errores ---
        if intent == "unknown":
            print(f"{INDENT_OUTPUT}[{self.name}] Orden desconocida.")
            self.set_emocion("confuso")
            self.speak("Perdona, no he entendido eso. ¿Me lo repites?")
            return
    
        # --- 3. Lógica de Tareas (Añadir, borrar, leer) ---
        # Si es una orden de compra real, avisamos al cerebro (Planner)
        self.publish_event(
            Event(type="voice_command", data={"intent": intent, "item": item, "quantity": quantity, "raw_text": raw_text}, origin=self.name)
        )
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
        audio_bytes = self.text_to_speech(text)

    def loop(self):
        self.process_audio()
        self.renderizar_ojos() 
        
        if self.emocion_actual != "neutral" and time.time() - self.ultimo_cambio_emocion > 4.0:
            self.set_emocion("neutral")