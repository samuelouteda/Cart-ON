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
        
        # URL actualizada a tu backend Dual Oficial
        self.cloud_url = "https://cart-on-api-sm-225606614592.europe-west1.run.app/api/v1/interaccion"

        self.speaker = Speaker("Speaker", event_bus, shared_data)
        self.display = Display("Display", event_bus, shared_data)
        self.ojos = RobotEyes("Eyes")

        # Mochila local
        self.lista_compra_local = shared_data.get('shopping_list', {}).copy()

        self.estado_fisico = "HABLA"  # Puede ser: "HABLA", "MAPEO" o "CONDUCCION"

        vosk.SetLogLevel(-1)

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
            
            # INYECCIÓN SM: Extraemos el modo de la nube
            modo_actual = datos_nube.get("modo", "desconocido").upper()
            texto_footer = f"Cart-ON (Físico) | MODO: {modo_actual}"
            
            # Extraemos la acción física que nos indica el Planner
            accion_fisica = datos_nube.get("accion_fisica", "NINGUNA")
            
            if "lista_compra" in datos_nube:
                self.lista_compra_local = datos_nube["lista_compra"]

            aula_recibida = datos_nube.get("aula", None)
            lat_recibida = datos_nube.get("lat", None)
            lng_recibida = datos_nube.get("lng", None)
            ruta_supermercado = datos_nube.get("ruta_supermercado", [])
            
            self.ojos.set_emocion(emocion_recibida)
            
            imagen_mapa = None
            if aula_recibida and lat_recibida and lng_recibida:
                print(f"{INDENT_OUTPUT}[{self.name}] Base de Datos detectó localización para el aula {aula_recibida}. Invocando Google Maps...")
                maps_key = os.getenv("MAPS_API_KEY")
                imagen_mapa = generate_location_image(aula_recibida, lat_recibida, lng_recibida, maps_key)
            
            self.display.update_data(
                status="SPEAKING", 
                title=f"Ruta a {aula_recibida}" if aula_recibida else "Respuesta Asistente",
                robot_text=texto,
                image=imagen_mapa,
                data_dict=self.lista_compra_local,
                footer=texto_footer  # Pasamos el footer (recuerda que tu display.py de la Raspi debe aceptarlo)
            )
            
            print(f"\n{INDENT_OUTPUT}[{self.name}] [Cart-ON Dice]: {texto}\n")
            
            # Ejecución de estado físico (Se mantiene fuera del hilo para ejecutar de inmediato)
            if accion_fisica == "INICIAR_MAPEO":
                self.estado_fisico = "MAPEO"
                print(f"{INDENT_OUTPUT}[{self.name}] FSM: Cambiando estado a MAPEO. Despertando LIDAR...")
                self.publish_event(Event(origin=self.name, type="START_MAPPING"))
                
            elif accion_fisica == "INICIAR_CONDUCCION":
                self.estado_fisico = "CONDUCCION"
                print(f"{INDENT_OUTPUT}[{self.name}] Cambiando estado a CONDUCCIÓN")
                datos_navegacion = {
                    "aula": aula_recibida,
                    "lat": lat_recibida,
                    "lng": lng_recibida,
                    "ruta_supermercado": ruta_supermercado   
                }
                self.publish_event(Event(origin=self.name, type="START_DRIVING", data=datos_navegacion))

            # =======================================================
            # HILO SECUNDARIO DE AUDIO (Para no congelar la LilyGo)
            # =======================================================
            def _reproducir_y_liberar():
                if audio_b64:
                    try:
                        audio_bytes = base64.b64decode(audio_b64)
                        self.speaker.play_audio(audio_bytes)
                    except Exception as e:
                        print(f"{INDENT_OUTPUT}[{self.name}] Error al delegar audio al Speaker: {e}")

                time.sleep(0.5) # Pausa respiratoria anti-ecos
                
                # Volvemos a abrir el semáforo para escuchar
                self.puedo_escuchar.set()

            threading.Thread(target=_reproducir_y_liberar, daemon=True).start()

        elif task.type == "PHYSICAL_ACTION_DONE":
            self.estado_fisico = "HABLA"
            print(f"\n{INDENT_OUTPUT}[{self.name}] FSM: Acción física completada. Cart-ON vuelve al estado de HABLA.")
            self.display.update_data(status="SUCCESS", title="DESTINO ALCANZADO", robot_text="He llegado. ¿En qué más te ayudo?", image=None)
            self.puedo_escuchar.set()

    def _hacer_peticion(self, frase, foto_bytes):
        try:
            if not foto_bytes or foto_bytes == b'\x00':
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
            print(f"{INDENT_OUTPUT}[{self.name}] ERROR: No encuentro Vosk.")
            return

        modelo = vosk.Model(ruta_modelo)
        recognizer_vosk = vosk.KaldiRecognizer(modelo, 16000)
        pa = pyaudio.PyAudio()

        index_micro_usb = None
        for i in range(pa.get_device_count()):
            dev_info = pa.get_device_info_by_index(i)
            if "USB ENC" in dev_info.get('name', '') or "hw:3,0" in dev_info.get('name', ''):
                index_micro_usb = i
                break
        
        necesita_despertar = True

        while self.running:
            self.puedo_escuchar.wait() 
            
            if necesita_despertar:
                # Si está mapeando o conduciendo, no pide que le llamen Cartón
                if self.estado_fisico == "HABLA":
                    print(f"\n{INDENT_OUTPUT}[{self.name}] Cart-ON en reposo. Di 'Cartón' para despertarlo...")
                
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
                        
                        # Parada emergencia por voz
                        if "para" in texto_detectado or "emergencia" in texto_detectado or "stop" in texto_detectado:
                            if self.estado_fisico in ["CONDUCCION", "MAPEO"]:
                                print(f"\n{INDENT_OUTPUT}[{self.name}] ¡PARADA DE EMERGENCIA POR VOZ DETECTADA!")
                                self.publish_event(Event(origin=self.name, type="EMERGENCY_STOP"))
                                self.estado_fisico = "HABLA" # Forzamos el reinicio al habla
                        
                        if "cartón" in texto_detectado or "carton" in texto_detectado:
                            wake_word_detectada = True

                stream.stop_stream()
                stream.close()
                necesita_despertar = False

            if not self.running: break
            
            try:
                with sr.Microphone(device_index=index_micro_usb) as source:
                    recognizer_google.adjust_for_ambient_noise(source, duration=1)
                    print(f"{INDENT_OUTPUT}[{self.name}] Te escucho... (Tienes 40s para hablar)")
                    # MEJORA SM: Ampliamos a 40 segundos de espera
                    audio = recognizer_google.listen(source, timeout=40, phrase_time_limit=40)

                self.puedo_escuchar.clear()
                print(f"{INDENT_OUTPUT}[{self.name}] Traduciendo tu voz a texto...")
                
                texto = recognizer_google.recognize_google(audio, language="es-ES")
                print(f"{INDENT_OUTPUT}[{self.name}] Has dicho: '{texto.lower()}'")

                if texto.lower() == 'salir':
                    self.publish_event(Event(origin=self.name, type="SHUTDOWN"))
                    break
                elif texto.strip():
                    # Interceptor estado físico
                    if self.estado_fisico == "CONDUCCION":
                        if "para" in texto.lower() or "detente" in texto.lower():
                            print(f"{INDENT_OUTPUT}[{self.name}] Orden de parada normal enviada al navegador.")
                            self.publish_event(Event(origin=self.name, type="EMERGENCY_STOP"))
                            self.estado_fisico = "HABLA"
                        else:
                            print(f"{INDENT_OUTPUT}[{self.name}] Silenciado localmente: El robot está ocupado conduciendo.")
                            self.display.update_data(robot_text="Shhh, estoy concentrado conduciendo. Di 'PARA' si hay peligro.")
                        self.puedo_escuchar.set()
                        necesita_despertar = True
                        
                    elif self.estado_fisico == "MAPEO":
                        print(f"{INDENT_OUTPUT}[{self.name}] Silenciado localmente: El robot está escaneando el entorno.")
                        self.puedo_escuchar.set()
                        necesita_despertar = True
                        
                    else:
                        # Flujo HABLA normal: Lo mandamos a la nube
                        self.publish_event(Event(origin=self.name, type="VOICE_DETECTED", data=texto))
                        necesita_despertar = False  # <--- MEJORA SM: Mantenemos la fluidez de conversación
                    
            except sr.WaitTimeoutError:
                print(f"{INDENT_OUTPUT}[{self.name}] 40 segundos de inactividad. Vuelvo a dormir zZz...")
                necesita_despertar = True
            except sr.UnknownValueError:
                print(f"{INDENT_OUTPUT}[{self.name}] No te he entendido bien. Inténtalo de nuevo...")
                necesita_despertar = False # Permite que siga escuchando directamente si falla en entender
                self.puedo_escuchar.set() 
            except Exception as e:
                if self.running:
                    print(f"{INDENT_OUTPUT}[{self.name}] Error en el micro: {e}")
                    necesita_despertar = True
                    self.puedo_escuchar.set()
        
    def loop(self):
        if self.puedo_escuchar.is_set():
            if self.estado_fisico == "HABLA":
                self.display.update_data(status="LISTENING", text="Esperando entrada por voz...")
            elif self.estado_fisico == "CONDUCCION":
                self.display.update_data(status="PROCESSING", text="ROBOT EN MOVIMIENTO...")
        
        ahora = time.time()
        if ahora - self.ultimo_refresco >= 0.05: 
            self.display.refresh()
            self.ultimo_refresco = ahora