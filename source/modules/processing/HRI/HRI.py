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

from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
from core.task import Task
from modules.actuation.speaker import Speaker
from modules.actuation.display import Display
from modules.actuation.eyes import RobotEyes
from modules.processing.HRI.maps_helper import generate_location_image

def normalize_for_display(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.replace("ñ", "n").replace("Ñ", "N")
    ascii_text = ascii_text.replace("ç", "c").replace("Ç", "C")
    return ascii_text

class HRI(BaseModule):
    def __init__(self, name, event_bus, shared_sensor_stream, api_key, data_task_bus, shared_data):
        super().__init__(name, event_bus)
        self.sensor_stream = shared_sensor_stream
        self.api_key = api_key
        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        
        # Ojo: Asegúrate de que esta URL sea la de tu backend correcto
        self.cloud_url = "https://cart-on-api-sm-225606614592.europe-west1.run.app/api/v1/interaccion"

        self.speaker = Speaker("Speaker", event_bus, shared_data)
        self.display = Display("Display", event_bus, shared_data)
        self.ojos = RobotEyes("Eyes")

        # Memoria local de la lista
        self.lista_compra_local = shared_data.get('shopping_list', {}).copy()

        # Silenciamos los logs molestos de Vosk
        vosk.SetLogLevel(-1)

        # Semáforo para controlar cuándo escuchar
        self.puedo_escuchar = threading.Event()
        self.puedo_escuchar.set()

        threading.Thread(target=self._escuchar_microfono, daemon=True).start()
        self.ultimo_refresco = time.time()

    def get_audio(self): 
        return self.sensor_stream['audio']

    def consume_audio(self):
        self.sensor_stream['audio'] = None
    
    def read_audio(self):
        audio = self.sensor_stream['audio']
        self.consume_audio()
        return audio
    
    def add_data_task(self, task):
        self.data_task_bus.put(task)

    def handle_task(self, task):
        if task.type == "SEND_TO_CLOUD":
            self.puedo_escuchar.clear() 
            
            texto_usuario = task.data
            foto_bytes = self.sensor_stream.get("last_frame", b'\x00')
            
            self.display.update_data(
                status="PROCESSING", 
                text=texto_usuario, 
                robot_text="", 
                title="Conectando al Cloud...",
                data_dict=self.shared_data.get('shopping_list', {})
            )
            self.display.refresh()
            
            respuesta = self._hacer_peticion(texto_usuario, foto_bytes)
            self.publish_event(Event(origin=self.name, type="CLOUD_RESPONSE", data=respuesta))
            
        elif task.type == "SPEAK":
            datos_nube = task.data
            
            emocion_recibida = datos_nube.get("emocion", "neutro")
            texto = datos_nube.get("texto", "Error en la respuesta")
            audio_b64 = datos_nube.get("audio_b64", None)
            
            # Extraemos el modo de la nube para mostrarlo en pantalla
            modo_actual = datos_nube.get("modo", "desconocido").upper()
            texto_footer = f"Sistema Cart-ON (Local) | MODO: {modo_actual}"
            
            if "lista_compra" in datos_nube:
                self.lista_compra_local = datos_nube["lista_compra"]

            aula_recibida = datos_nube.get("aula", None)
            lat_recibida = datos_nube.get("lat", None)
            lng_recibida = datos_nube.get("lng", None)
            
            self.ojos.set_emocion(emocion_recibida)
            
            imagen_mapa = None
            if aula_recibida and lat_recibida and lng_recibida:
                print(f"{INDENT_OUTPUT}[{self.name}] Base de Datos detectó localización para el aula {aula_recibida}. Invocando Google Maps...")
                maps_key = os.getenv("MAPS_API_KEY")
                imagen_mapa = generate_location_image(aula_recibida, lat_recibida, lng_recibida, maps_key)
            
            # Actualizamos la pantalla ANTES de hablar y le pasamos el footer
            self.display.update_data(
                status="SPEAKING", 
                title=f"Ruta a {aula_recibida}" if aula_recibida else "Respuesta Asistente",
                robot_text=texto,
                image=imagen_mapa,
                data_dict=self.lista_compra_local,
                footer=texto_footer
            )
            
            print(f"\n{INDENT_OUTPUT}[{self.name}] [Cart-ON Dice]: {texto}\n")
            
            # =======================================================
            # HILO SECUNDARIO DE AUDIO (Para no congelar OpenCV)
            # =======================================================
            def _reproducir_y_liberar():
                if audio_b64:
                    try:
                        audio_bytes = base64.b64decode(audio_b64)
                        self.speaker.play_audio(audio_bytes)
                    except Exception as e:
                        print(f"{INDENT_OUTPUT}[{self.name}] Error al reproducir audio: {e}")

                time.sleep(0.5) # Pequeña pausa respiratoria
                
                # Volvemos a abrir el micrófono después de hablar
                self.puedo_escuchar.set()

            # Lanzamos el audio en un hilo aparte para que la pantalla siga refrescándose
            threading.Thread(target=_reproducir_y_liberar, daemon=True).start()

    def _hacer_peticion(self, frase, foto_bytes):
        try:
            if not foto_bytes or foto_bytes == b'\x00':
                # Imagen JPEG mínima por defecto
                foto_bytes = (b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
                              b'\xff\xdb\x00C\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                              b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                              b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                              b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                              b'\xff\xff\xff\xff\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01'
                              b'\x11\x00\xff\xc4\x00\x07\x00\x00\x00\x00\x00\x00\x00\xff\xda'
                              b'\x00\x08\x01\x01\x00\x00\x3f\x00\x37\xff\xd9')

            archivos = {'image_file': ('frame.jpg', foto_bytes, 'image/jpeg')}
            lista_a_enviar = self.lista_compra_local if self.lista_compra_local else self.shared_data.get('shopping_list', {})
            
            datos = {
                'frase_usuario': frase,
                'lista_compra': json.dumps(lista_a_enviar, ensure_ascii=False)
            }
            
            res = requests.post(self.cloud_url, files=archivos, data=datos, timeout=30)
            res.raise_for_status()
            return res.json()
            
        except requests.exceptions.RequestException as e:
            print(f"{INDENT_OUTPUT}[{self.name}] Error conexión: {e}")
            self.puedo_escuchar.set()
            return {"status": "error", "texto": "Mis antenas no conectan con internet."}

    def _escuchar_microfono(self):
        recognizer_google = sr.Recognizer()
        ruta_modelo = os.path.join(os.path.dirname(__file__), "vosk-model-small-es-0.42")
        
        if not os.path.exists(ruta_modelo):
            print(f"{INDENT_OUTPUT}[{self.name}] ERROR: No encuentro el modelo Vosk en {ruta_modelo}")
            return

        modelo = vosk.Model(ruta_modelo)
        recognizer_vosk = vosk.KaldiRecognizer(modelo, 16000)
        pa = pyaudio.PyAudio()
        
        necesita_despertar = True

        while self.running:
            self.puedo_escuchar.wait() 
            
            if not self.running: break

            if necesita_despertar:
                print(f"\n{INDENT_OUTPUT} Cart-ON en reposo. Di 'Cartón' para despertarlo...")
                self.display.update_data(status="IDLE", text="Di 'Cartón' para despertar...")
                
                # Usará el micro por defecto del PC al no especificar input_device_index
                stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4000)
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
                        
                        if "cartón" in texto_detectado or "carton" in texto_detectado:
                            wake_word_detectada = True

                stream.stop_stream()
                stream.close()
                necesita_despertar = False

            if not self.running: break
            
            try:
                # Usará el micro por defecto del PC
                with sr.Microphone() as source:
                    recognizer_google.adjust_for_ambient_noise(source, duration=0.5)
                    self.display.update_data(status="LISTENING", text="Te escucho...")
                    print(f"{INDENT_OUTPUT}[{self.name}] Te escucho... (Tienes 40s para hablar)")
                    audio = recognizer_google.listen(source, timeout=40, phrase_time_limit=40)

                self.puedo_escuchar.clear()
                self.display.update_data(status="PROCESSING", text="Traduciendo voz a texto...")
                print(f"{INDENT_OUTPUT}[{self.name}] Traduciendo tu voz a texto...")
                
                texto = recognizer_google.recognize_google(audio, language="es-ES")
                print(f"{INDENT_OUTPUT}[{self.name}] Has dicho: '{texto}'")

                if texto.lower() == 'salir':
                    self.publish_event(Event(origin=self.name, type="SHUTDOWN"))
                    break
                elif texto.strip():
                    # Flujo normal multimedia
                    self.publish_event(Event(origin=self.name, type="VOICE_DETECTED", data=texto))
                    necesita_despertar = False  # <--- Mantenemos al robot despierto para que la conversación fluya
                    
            except sr.WaitTimeoutError:
                print(f"{INDENT_OUTPUT}[{self.name}] 40 segundos de inactividad. Vuelvo a dormir zZz...")
                self.display.update_data(status="IDLE", text="Di 'Cartón' para despertar...")
                necesita_despertar = True  # <--- SOLO se va a dormir si pasan los 40 segundos

            except sr.UnknownValueError:
                print(f"{INDENT_OUTPUT}[{self.name}] No he entendido, repite por favor...")
                self.puedo_escuchar.set() 
                
            except Exception as e:
                if self.running:
                    print(f"{INDENT_OUTPUT}[{self.name}] Error en el micrófono: {e}")
                    self.puedo_escuchar.set()
                    time.sleep(1) # Pausa de seguridad si el micro falla

    def loop(self):
        ahora = time.time()
        # Refrescamos la pantalla a 20 FPS (0.05s)
        if ahora - self.ultimo_refresco >= 0.05: 
            self.display.refresh()
            self.ultimo_refresco = ahora