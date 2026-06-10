import threading
import requests
import time
import os
import base64
import tempfile
import speech_recognition as sr
import json
from modules.actuation.display import Display
from modules.actuation.maps_helper import generate_location_image

# Importamos Vosk para el Wake Word Offline
import vosk
import pyaudio

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

from modules.actuation.display import Display

# Silenciamos pygame antes de importarlo
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

class HRI(BaseModule):
    def __init__(self, name, event_bus, sensor_data, api_key):
        super().__init__(name, event_bus)
        self.sensor_data = sensor_data
        self.api_key = api_key
        self.cloud_url = "https://cart-on-api-225606614592.europe-southwest1.run.app/api/v1/interaccion"
        
        self.puedo_escuchar = threading.Event()
        self.puedo_escuchar.set()
        
        # INICIALIZAMOS LA PANTALLA
        self.display = Display("Display", event_bus, shared_data={})
        
        try:
            pygame.mixer.init()
            print(f"{INDENT_OUTPUT}[{self.name}] 🔊 Motor de audio pre-cargado y listo.")
        except Exception as e:
            print(f"{INDENT_OUTPUT}[{self.name}] 🔴 Aviso: No se pudo iniciar el audio: {e}")
        
        # Ocultar los logs molestos de Vosk en la terminal
        vosk.SetLogLevel(-1)
        
        threading.Thread(target=self._escuchar_microfono, daemon=True).start()

    def handle_task(self, task):
        if task.type == "SEND_TO_CLOUD":
            # 🔴 Ponemos el semáforo en rojo para bloquear el teclado mientras piensa
            self.puedo_escuchar.clear() 
            
            texto_usuario = task.data
            foto_bytes = self.sensor_data.get("last_frame", b'\x00')
            
            self.display.update_data(
                status="PROCESSING", 
                text=texto_usuario, 
                robot_text="", 
                title="Conectando al Cloud...",
                data_dict={}
            )
            self.display.refresh()
            
            print(f"{INDENT_OUTPUT}[{self.name}] ☁️ Conectando a la nube...")
            respuesta = self._hacer_peticion(texto_usuario, foto_bytes)
            
            self.publish_event(Event(origin=self.name, type="CLOUD_RESPONSE", data=respuesta))
            
        elif task.type == "SPEAK":
            # Extraemos el paquete que viene de la nube
  
            datos_nube = task.data
            texto = datos_nube.get("texto", "Error en la respuesta")
            audio_b64 = datos_nube.get("audio_b64", None)
            aula_recibida = datos_nube.get("aula", None) # 📍 Leemos el aula de la nube

            print(f"\n{INDENT_OUTPUT}🤖 [Cart-ON Dice]: {texto}\n")
            
            # --- MAGIA MULTIMEDIA: GENERAMOS MAPA SI HAY AULA ---
            aula_recibida = datos_nube.get("aula", None)
            lat_recibida = datos_nube.get("lat", None)
            lng_recibida = datos_nube.get("lng", None)

            imagen_mapa = None
            # Si nos llega el aula y además tiene coordenadas en la BD
            if aula_recibida and lat_recibida and lng_recibida:
                maps_key = os.getenv("MAPS_API_KEY")
                imagen_mapa = generate_location_image(aula_recibida, lat_recibida, lng_recibida, maps_key)
            
            self.display.update_data(
                status="SPEAKING", 
                title=f"Ruta a {aula_recibida}" if aula_recibida else "Respuesta Asistente",
                robot_text=texto,
                image=imagen_mapa
            )
            
            print(f"\n{INDENT_OUTPUT}🤖 [Cart-ON Dice]: {texto}\n")
            
            # Si la nube nos ha mandado un audio, lo reproducimos
            if audio_b64:
                try:
                    audio_bytes = base64.b64decode(audio_b64)
                    
                    # Guardamos el MP3 temporalmente
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                        fp.write(audio_bytes)
                        temp_path = fp.name
                        
                    # Reproducimos el archivo
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    
                    # Pausamos el código de este hilo hasta que el robot termine de hablar
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                        
                    # Liberamos el archivo para que Windows nos deje borrarlo limpiamente
                    pygame.mixer.music.unload()
                    os.remove(temp_path)
                except Exception as e:
                    print(f"{INDENT_OUTPUT}🔴 Error al reproducir audio: {e}")

            # 🟢 Ponemos el semáforo en verde otra vez tras hablar
            self.puedo_escuchar.set()

    def _hacer_peticion(self, frase, foto_bytes):
        try:
            # === MODIFICACIÓ DE SEGURETAT DE LA FOTO ===
            # Si 'foto_bytes' és buit o és el b'\x00' per defecte, 
            # generem una mini-imatge JPEG vàlida de 1x1 píxel transparent 
            # perquè el Cloud no exploti amb un Error 500.
            if not foto_bytes or foto_bytes == b'\x00':
                # Això és el codi binari d'un JPEG real mínim de 1x1 píxels
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
            datos = {'frase_usuario': frase}
            
            # Fem el POST real
            res = requests.post(self.cloud_url, files=archivos, data=datos, timeout=15)
            
            # Si el Cloud respon amb un error de codi (ex: 500 o 400), saltarà l'excepció
            res.raise_for_status()
            return res.json()
            
        except requests.exceptions.RequestException as e:
            # Imprimim l'error real a la terminal de la Raspy per saber QUÈ es queixa el Cloud
            print(f"{INDENT_OUTPUT}🔴 Detall del error de connexió al Cloud: {e}")
            
            # Si falla, liberamos el semáforo para no quedarnos atascados
            self.puedo_escuchar.set()
            return {"status": "error", "texto": "Perdona, mis antenas no conectan con internet."}

    def _escuchar_microfono(self):
        recognizer_google = sr.Recognizer()
        
        # Cargamos el modelo local de Vosk
        ruta_modelo = os.path.join(os.path.dirname(__file__), "model_vosk")
        if not os.path.exists(ruta_modelo):
            print(f"{INDENT_OUTPUT}[{self.name}] 🔴 ERROR: No encuentro la carpeta 'modelo_vosk'.")
            return

        modelo = vosk.Model(ruta_modelo)
        recognizer_vosk = vosk.KaldiRecognizer(modelo, 16000)
        pa = pyaudio.PyAudio()

        # 🔍 BUSCAMOS EL ÍNDICE DE TU MICRÓFONO "USB ENC Audio Device" (card 3)
        index_micro_usb = None
        for i in range(pa.get_device_count()):
            dev_info = pa.get_device_info_by_index(i)
            # Buscamos por nombre o por coincidencia de la tarjeta de sonido
            if "USB ENC" in dev_info.get('name', '') or "hw:3,0" in dev_info.get('name', ''):
                index_micro_usb = i
                print(f"{INDENT_OUTPUT}[{self.name}] 🎙️ Micrófono USB detectado en PyAudio (Índice {i}): {dev_info['name']}")
                break
        
        # Si por lo que sea cambia de puerto y no lo encuentra por nombre, forzamos el de la Card 3
        if index_micro_usb is None:
            print(f"{INDENT_OUTPUT}[{self.name}] ⚠️ Aviso: No se detectó por nombre exacto. Forzando índice compatible...")
            index_micro_usb = None # Dejará que SpeechRecognition y PyAudio usen el mapeo por defecto o Card 3

        # 🧠 VARIABLE CLAVE: Controla si obligamos a decir la Wake Word
        necesita_despertar = True

        while self.running:
            self.puedo_escuchar.wait() 
            
            # --- FASE 1: ESPERAR LA WAKE WORD (Solo si viene de reposo) ---
            if necesita_despertar:
                print(f"\n{INDENT_OUTPUT}💤 Cart-ON en reposo. Di 'Cartón' para despertarlo...")
                
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,           # Tornem als 16000 que demana Vosk de forma nativa
                    input=True,
                    frames_per_buffer=4000  # Reduït a 4000 per evitar desbordaments de buffer a ALSA
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
                        
                        if texto_detectado.strip():
                            print(f"{INDENT_OUTPUT} [Vosk Escoltat en repòs]: '{texto_detectado}'")
                        
                        if "cartón" in texto_detectado or "carton" in texto_detectado or "carto" in texto_detectado:
                            print(f"\n{INDENT_OUTPUT}🔔 ¡Wake Word ('Cart-ON') Detectada!")
                            wake_word_detectada = True

                stream.stop_stream()
                stream.close()
                # 🔓 Abrimos la conversación. Ya no necesita despertarse.
                necesita_despertar = False

            if not self.running: break
            
            # --- FASE 2: CONVERSACIÓN CONTINUA (10s de gracia) ---
            try:
                with sr.Microphone(device_index=index_micro_usb) as source:
                    recognizer_google.adjust_for_ambient_noise(source, duration=1)  # (Línia nova de filtrat)
                    print(f"{INDENT_OUTPUT}🟢 Te escucho... (Tienes 10s para hablar)")
                    # timeout=10: Si pasan 10 segundos en silencio, explota con WaitTimeoutError
                    audio = recognizer_google.listen(source, timeout=10, phrase_time_limit=10)

                self.puedo_escuchar.clear()
                print(f"{INDENT_OUTPUT}⏳ Traduciendo tu voz a texto...")
                
                texto = recognizer_google.recognize_google(audio, language="es-ES")
                print(f"{INDENT_OUTPUT}🗣️ Has dicho: '{texto}'")

                if texto.lower() == 'salir':
                    self.publish_event(Event(origin=self.name, type="SHUTDOWN"))
                    break
                elif texto.strip():
                    self.publish_event(Event(origin=self.name, type="VOICE_DETECTED", data=texto))
                    # IMPORTANTE: NO ponemos necesita_despertar = True aquí. 
                    # Así, cuando el robot termine de hablar, saltará directo a escuchar de nuevo.
                    
            except sr.WaitTimeoutError:
                print(f"{INDENT_OUTPUT}🥱 10 segundos de inactividad. Vuelvo a dormir zZz...")
                necesita_despertar = True   # Torna a adormir-se
                # No cal fer .set() perquè el loop principal s'aturarà a esperar la Wake Word
            except sr.UnknownValueError:
                print(f"{INDENT_OUTPUT}🤷 No te he entendido bien. Inténtalo de nuevo...")
                self.puedo_escuchar.set() 
            except Exception as e:
                if self.running:
                    print(f"{INDENT_OUTPUT}🔴 Error en el micro: {e}")
                    necesita_despertar = True   # Si el micro falla, ens protegim adormint el robot
                    self.puedo_escuchar.set()
        
    def loop(self):
        """
        Bucle asíncron executat contínuament pel mòdul HRI de fons.
        S'encarrega de mantenir la finestra d'OpenCV activa i processar els píxels.
        """
        # Si el robot no està parlant ni processant, mantenim visualment l'estat d'escolta
        if self.puedo_escuchar.is_set():
            self.display.update_data(status="LISTENING", text="Esperando entrada por voz...")

        # Executem el mètode refresh de la Fase 1 per evitar congelacions de la pantalla
        self.display.refresh()