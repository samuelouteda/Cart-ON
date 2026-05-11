import pygame
import os
import time

def init_speaker():
    # inicializa el canal de hardware de audio
    pygame.mixer.init()

def play_audio(audio_bytes):
    # recibe un flujo de bytes puros y los ejecuta en el hardware (altavoces)
    if not audio_bytes:
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