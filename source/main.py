from queue import Queue
from dotenv import load_dotenv
import os
import sys
import time

# Tus módulos locales (ahora en versión Thin Edge)
from modules.decision_making.planner import Planner
from modules.processing.navigation.navigation import Navigation
from modules.sensor.sensor import SensoryModule
from modules.processing.HRI.HRI import HRI

# IMPORTANTE: Importamos el objeto Event para el apagado limpio
from core.event import Event

def main():
    print("==================================================")
    print(" ☁️ INICIANDO CART-ON (EVENT-DRIVEN THIN EDGE) ☁️")
    print("==================================================")

    event_bus = Queue()
    sensor_data = {}
    shared_data = {} # Para almacenar cosas temporales como el estado de la batería o la IP

    # Cargar variables de entorno
    load_dotenv()

    # ⚠️ ATENCIÓN: Solo cargamos la clave de voz. La de Gemini ya está en la nube.
    api_key = os.getenv("API_KEY")             

    if not api_key:
        print("Error crítico: falta la API_KEY (Voz STT/TTS) en el archivo .env")
        sys.exit(1)

    # 1. Instanciamos los módulos (pasándoles el bus para que hablen entre ellos)
    planner = Planner("Planner", event_bus)
    navigation = Navigation("Navigation", event_bus, sensor_data)
    sensory = SensoryModule("Sensory", event_bus, sensor_data)
    
    # El HRI ya no recibe la clave de Gemini, solo la de Google Cloud Voz
    human_interaction = HRI("HRI", event_bus, sensor_data, api_key)

    # 2. Conectamos los módulos al cerebro
    planner.append_modules([navigation, sensory, human_interaction])

    # 3. Arrancamos los hilos (Multithreading)
    planner.start()
    navigation.start()
    sensory.start()
    human_interaction.start()

    try:
        # Bucle de vigilancia del hilo principal
        while True:
            time.sleep(1) 
    except KeyboardInterrupt:
        # Capturamos el primer Ctrl+C silenciosamente
        pass
    finally:
        print("\n[Main] 🛑 Cierre manual detectado (Ctrl+C). Apagando robot...")
        
        # Gritamos al bus con un OBJETO EVENT real para que todos los hilos se apaguen
        event_bus.put(Event(origin="Main", type="SHUTDOWN"))
        
        # Envolvemos los join en otro try-except por si haces Ctrl+C varias veces seguidas por impaciencia
        try:
            planner.join(timeout=2)
            human_interaction.join(timeout=2)
            navigation.join(timeout=2)
            sensory.join(timeout=2)
        except KeyboardInterrupt:
            pass
            
        print("[Main] ✅ Sistema cerrado limpiamente.")

if __name__ == "__main__":
    main()