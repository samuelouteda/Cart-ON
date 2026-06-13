import threading
import requests
import time
import os
import base64
import speech_recognition as sr
import json
import unicodedata
import vosk
import pyaudio

# Silenciamos pygame antes de importarlo
#os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
#import pygame

from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
from core.task import Task
from modules.actuation.speaker import Speaker
from modules.actuation.display import Display
from modules.actuation.eyes import RobotEyes
from modules.processing.HRI.maps_helper import generate_location_image

def normalize_for_display(text: str) -> str:
    # Normalitza accents (á → a, é → e, ñ → n...)
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Substitucions manuals opcionals
    ascii_text = ascii_text.replace("ñ", "n").replace("Ñ", "N")
    ascii_text = ascii_text.replace("ç", "c").replace("Ç", "C")

    return ascii_text

class HRI(BaseModule):
    """
    Layer 2: Human-Robot Interaction Module
    """

    def __init__(self, name, event_bus, shared_sensor_stream, api_key, data_task_bus, shared_data):
        super().__init__(name, event_bus)
        self.sensor_stream = shared_sensor_stream
        self.api_key = api_key
        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        self.cloud_url = "https://cart-on-api-225606614592.europe-west1.run.app/api/v1/interaccion"

        self.speaker = Speaker("Speaker", event_bus, shared_data)
        self.display = Display("Display", event_bus, shared_data)
        self.ojos = RobotEyes()

        # 🛒 MOCHILA LOCAL PARA LA LISTA DE LA COMPRA (Evita la amnesia de la nube)
        self.lista_compra_local = {}

        # Ocultar logs de Vosk
        vosk.SetLogLevel(-1)

        # Semáforo para gestionar cuándo se puede escuchar
        self.puedo_escuchar = threading.Event()
        self.puedo_escuchar.set()

        # Arrancamos el hilo de escucha independiente
        threading.Thread(target=self._escuchar_microfono, daemon=True).start()

        self.ultimo_refresco = time.time()

    def get_audio(self): 
        """Reads audio without consuming it"""
        return self.sensor_stream['audio']

    def consume_audio(self):
        """Consumes (deletes) the audio data"""
        self.sensor_stream['audio'] = None
    
    def read_audio(self):
        """Reads audio data and then consumes it"""
        audio = self.sensor_stream['audio']
        self.consume_audio()
        return audio
    
    def add_data_task(self, task):
        self.data_task_bus.put(task)

    def handle_task(self, task):
        if task.type == "SEND_TO_CLOUD":
            print(f"{INDENT_OUTPUT}[{self.name}] Task recibida: {task.type}")
            # Bloqueamos la escucha
            self.puedo_escuchar.clear() 
            
            texto_usuario = task.data
            foto_bytes = self.sensor_stream.get("last_frame", b'\x00')
            
            self.display.update_data(
                status="PROCESSING", 
                text=texto_usuario, 
                robot_text="", 
                title="Conectando al Cloud...",
                data_dict={}
            )
            self.display.refresh()
            
            print(f"{INDENT_OUTPUT}[{self.name}] Conectando a la nube...")
            respuesta = self._hacer_peticion(texto_usuario, foto_bytes)
            
            self.publish_event(Event(origin=self.name, type="CLOUD_RESPONSE", data=respuesta))
            
        elif task.type == "SPEAK":
            # Extraemos el paquete del cloud
            datos_nube = task.data
            emocion_recibida = datos_nube.get("emocion", "neutro")
            texto = datos_nube.get("texto", "Error en la respuesta")
            audio_b64 = datos_nube.get("audio_b64", None)
            
            # 🛒 ACTUALIZAMOS LA MOCHILA LOCAL DE LA COMPRA
            if "lista_compra" in datos_nube:
                self.lista_compra_local = datos_nube["lista_compra"]

            # 🛠️ CAPTURA DE DATOS GEOGRÁFICOS DE LA NUBE
            aula_recibida = datos_nube.get("aula", None)
            lat_recibida = datos_nube.get("lat", None)
            lng_recibida = datos_nube.get("lng", None)
            
            # Mandamos la emoción a tus ojos OLED
            self.ojos.set_emocion(emocion_recibida)
            
            print(f"⚡ [Recepción Nube] Ha llegado el paquete.")
            print(f"🎭 Cambiando cara del robot a modo: {emocion_recibida}")
            print(f"🔊 Hablando: '{texto}'")
                        
            # --- 🗺️ MAGIA MULTIMEDIA DE GOOGLE MAPS ---
            imagen_mapa = None
            if aula_recibida and lat_recibida and lng_recibida:
                print(f"🗺️ Base de Datos detectó localización para el aula {aula_recibida}. Invocando Google Maps...")
                maps_key = os.getenv("MAPS_API_KEY")
                imagen_mapa = generate_location_image(aula_recibida, lat_recibida, lng_recibida, maps_key)
            
            self.display.update_data(
                status="SPEAKING", 
                title=f"Ruta a {aula_recibida}" if aula_recibida else "Respuesta Asistente",
                robot_text=texto,
                image=imagen_mapa
            )
            
            print(f"\n{INDENT_OUTPUT} [Cart-ON Dice]: {texto}\n")
            
            # DELEGACIÓN AL SPEAKER (Separación de responsabilidades)
            if audio_b64:
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                    # Como play_audio ya tiene su propio bucle de bloqueo, esto esperará automáticamente
                    self.speaker.play_audio(audio_bytes)
                except Exception as e:
                    print(f"{INDENT_OUTPUT} Error al delegar audio al Speaker: {e}")

            # Ponemos el semáforo en verde tras reproducir
            self.puedo_escuchar.set()

    def _hacer_peticion(self, frase, foto_bytes):
        try:
            # JPEG de seguridad 1x1 si no hay foto
            if not foto_bytes or foto_bytes == b'\x00':
                foto_bytes = (
                    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
                    b'\xff\xdb\x00C\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    b'\xff\xff\xff\xff\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01'
                    b'\x11\x00\xff\xc4\x00\x07\x00\x00\x00\x00\x00\x00\x00\xff\xda'
                    b'\x00\x08\x01\x01\x00\x00\x3f\x00\x37\xff\xd9'
                )

            archivos = {'image_file': ('frame.jpg', foto_bytes, 'image/jpeg')}
            
            # 🛒 Añadimos la lista de la compra al paquete de datos para la nube
            datos = {
                'frase_usuario': frase,
                'lista_compra': json.dumps(self.lista_compra_local)
            }
            
            res = requests.post(self.cloud_url, files=archivos, data=datos, timeout=30)
            res.raise_for_status()
            return res.json()
            
        except requests.exceptions.RequestException as e:
            print(f"{INDENT_OUTPUT} Detalle del error de conexión: {e}")
            self.puedo_escuchar.set()
            return {"status": "error", "texto": "Perdona, mis antenas no conectan con internet."}

    def _escuchar_microfono(self):
        recognizer_google = sr.Recognizer()
        
        ruta_modelo = os.path.join(os.path.dirname(__file__), "vosk-model-small-es-0.42")
        print("La ruta es: ", ruta_modelo)
        if not os.path.exists(ruta_modelo):
            print(f"{INDENT_OUTPUT}[{self.name}]  ERROR: No encuentro la carpeta 'vosk-model-small-es-0.42'.")
            return

        modelo = vosk.Model(ruta_modelo)
        recognizer_vosk = vosk.KaldiRecognizer(modelo, 16000)
        pa = pyaudio.PyAudio()

        index_micro_usb = None
        for i in range(pa.get_device_count()):
            dev_info = pa.get_device_info_by_index(i)
            if "USB ENC" in dev_info.get('name', '') or "hw:3,0" in dev_info.get('name', ''):
                index_micro_usb = i
                print(f"{INDENT_OUTPUT}[{self.name}]  Micrófono USB detectado: {dev_info['name']}")
                break
        
        necesita_despertar = True

        while self.running:
            self.puedo_escuchar.wait() 
            
            # --- FASE 1: ESPERAR LA WAKE WORD ---
            if necesita_despertar:
                print(f"\n{INDENT_OUTPUT} Cart-ON en reposo. Di 'Cartón' para despertarlo...")
                
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=4000
                )
                stream.start_stream()
                
                wake_word_detectada = False
                while self.running and not wake_word_detectada:
                    if not self.puedo_escuchar.is_set():
                        time.sleep(0.1)
                        continue

                    data = stream.read(4000, exception_on_overflow=False)
                    if recognizer_vosk.AcceptWaveform(data):
                        resultado = json.loads(recognizer_vosk.Result())
                        texto_detectado = resultado.get("text", "").lower()
                        
                        if "cartón" in texto_detectado or "carton" in texto_detectado or "carto" in texto_detectado:
                            print(f"\n{INDENT_OUTPUT} ¡Wake Word ('Cart-ON') Detectada!")
                            wake_word_detectada = True

                stream.stop_stream()
                stream.close()
                necesita_despertar = False

            if not self.running: break
            
            # --- FASE 2: CONVERSACIÓN CONTINUA ---
            try:
                with sr.Microphone(device_index=index_micro_usb) as source:
                    recognizer_google.adjust_for_ambient_noise(source, duration=1)
                    print(f"{INDENT_OUTPUT} Te escucho... (Tienes 10s para hablar)")
                    audio = recognizer_google.listen(source, timeout=30, phrase_time_limit=10)

                self.puedo_escuchar.clear()
                print(f"{INDENT_OUTPUT} Traduciendo tu voz a texto...")
                
                texto = recognizer_google.recognize_google(audio, language="es-ES")
                print(f"{INDENT_OUTPUT} Has dicho: '{texto}'")

                if texto.lower() == 'salir':
                    self.publish_event(Event(origin=self.name, type="SHUTDOWN"))
                    break
                elif texto.strip():
                    # Lanzamos el texto para que el Planner responda con un SEND_TO_CLOUD
                    self.publish_event(Event(origin=self.name, type="VOICE_DETECTED", data=texto))
                    
            except sr.WaitTimeoutError:
                print(f"{INDENT_OUTPUT} 10 segundos de inactividad. Vuelvo a dormir zZz...")
                necesita_despertar = True
            except sr.UnknownValueError:
                print(f"{INDENT_OUTPUT} No te he entendido bien. Inténtalo de nuevo...")
                self.puedo_escuchar.set() 
            except Exception as e:
                if self.running:
                    print(f"{INDENT_OUTPUT} Error en el micro: {e}")
                    necesita_despertar = True
                    self.puedo_escuchar.set()
        
    def loop(self):
        if self.puedo_escuchar.is_set():
            self.display.update_data(status="LISTENING", text="Esperando entrada por voz...")
        
        ahora = time.time()
        if ahora - self.ultimo_refresco >= 0.05:  # 0.05s = 20 FPS
            self.display.refresh()
            self.ultimo_refresco = ahora