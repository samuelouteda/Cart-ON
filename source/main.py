from queue import Queue
from collections import deque as Deque
from dotenv import load_dotenv
import os
import sys

from modules.decision_making.planner import Planner
from modules.processing.navigation.navigation import Navigation
from modules.sensor.sensor import SensoryModule
from modules.processing.HRI.HRI import HRI
from modules.processing.data.data_manager import DataModule
from modules.processing.HRI.HRI_Wakeword import *
import time

#Netejaaaa
os.system('cls' if os.name == 'nt' else 'clear')

event_bus = Queue()
sensor_data = {}
shared_data = {} #Implementar sistema de almacenamiento compartido para datos no relacionados con sensores

# Cargar variables de entorno
load_dotenv()

# Extraer ambas claves
api_key = os.getenv("API_KEY")             #Google Cloud (STT/TTS)
gemini_api_key = os.getenv("GEMINI_API_KEY") #Google AI Studio (NLP)

# Validaciones de seguridad
if not api_key:
    print("Error crítico: falta la API_KEY (Voz) en el archivo .env")
    sys.exit(1)
    
if not gemini_api_key:
    print("Error crítico: falta la GEMINI_API_KEY (Cerebro) en el archivo .env")
    sys.exit(1)

planner = Planner(event_bus)
navigation = Navigation("Navigation", event_bus, sensor_data)
sensory = SensoryModule("Sensory", event_bus, sensor_data)

# Pasamos ambas claves al módulo de interacción
human_interaction = HRI("HRI", event_bus, sensor_data, api_key, gemini_api_key)
data_manager = DataModule("Data", event_bus)

wake = HRI_WakeWord("carton") #WakeWord!!1
planner.append_modules([navigation, sensory, human_interaction, data_manager])

planner.start()
navigation.start()
sensory.start()
human_interaction.start()
data_manager.start()

#planner.join(60)
while True:
    # 1. Esperar wake-word
    if wake.listen():
        print("\n[Sistema] Wake-word detectada! Activant HRI antic...\n")

        # 2. Activar el HRI antic (només quan es desperta)
        human_interaction.loop()  # ← funció que afegirem al HRI antic

        print("\n[Sistema] Tornant a mode wake-word...\n")
        time.sleep(0.5)