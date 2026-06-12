import pygame
import os
import time

from core.event import Event
from core.constants import INDENT_OUTPUT

class Speaker:
    def __init__(self, name, event_bus, shared_data):
        self.name = name
        self.event_bus = event_bus
        self.shared_data = shared_data

        self.init_speaker()

    def init_speaker(self):
       # PROTECCIÓN CLOUD / DOCKER: Si no hay hardware de sonido, capturamos el error
        try:
            pygame.mixer.init()
            self.hardware_disponible = True
            print(f"{INDENT_OUTPUT}[{self.name}] Motor de audio pre-cargado y listo.")
        except Exception as e:
            self.hardware_disponible = False
            print(f"{INDENT_OUTPUT}[{self.name}] Aviso: Hardware de sonido no disponible (Entorno Cloud/Docker): {e}")

    def play_audio(self, audio_bytes):
        # recibe un flujo de bytes puros y los ejecuta en el hardware (altavoces)
        if not audio_bytes:
            return
        
        # CONTROL CLOUD: Si no tenemos tarjeta de sonido física, saltamos la reproducción   
        if not getattr(self, 'hardware_disponible', True):
            return
         
        temp_filename = "respuesta_temp.mp3"
        
        try:
            # 1. interactuar con el sistema de archivos local para crear el medio fisico
            with open(temp_filename, "wb") as audio_file:
                audio_file.write(audio_bytes)
                
            # 2. enviar al hardware de audio
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            
            # 3. bloquear la ejecucion hasta que el buffer de audio termine
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
        except Exception as e:

            print(f"error de hardware de audio: {e}")
            
        finally:
            # 4. liberar recursos fisicos y limpiar
            if pygame.mixer.music.get_busy() == False:
                pygame.mixer.music.unload()
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)