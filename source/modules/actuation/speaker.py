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
        try:
            pygame.mixer.init()
            self.hardware_disponible = True
            print(f"{INDENT_OUTPUT}[{self.name}] Motor de audio multimedia cargado y listo.")
        except Exception as e:
            self.hardware_disponible = False
            print(f"{INDENT_OUTPUT}[{self.name}] Aviso: Hardware de sonido no disponible: {e}")

    def play_audio(self, audio_bytes):
        if not audio_bytes or not getattr(self, 'hardware_disponible', True):
            return
         
        temp_filename = "respuesta_temp.mp3"
        
        try:
            with open(temp_filename, "wb") as audio_file:
                audio_file.write(audio_bytes)
                
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[{self.name}] Error de reproducción de audio: {e}")
            
        finally:
            if pygame.mixer.music.get_busy() == False:
                pygame.mixer.music.unload()
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)