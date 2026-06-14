from queue import Queue
from dotenv import load_dotenv
import os
import sys
import time

# Importamos el Orquestador y las estructuras core
from core.event import Event
from modules.decision_making.planner import Planner

# Importamos los Módulos de Software (Multimedia)
from modules.sensor.sensor import SensoryModule
from modules.processing.HRI.HRI import HRI
from modules.processing.data.data_manager import DataModule

def main():
    print("[MAIN] Iniciando Cart-ON (Modo Sistemas Multimèdia)...")

    # Inicialización de colas y estructuras compartidas
    event_bus = Queue()
    data_task_bus = Queue()
    shared_sensor_stream = {}
    shared_data = {}

    load_dotenv()
    api_key = os.getenv("API_KEY")

    if not api_key:
        print("[MAIN] Error: Falta la API_KEY en el archivo .env")
        sys.exit(1)

    # Instanciación de módulos de procesamiento puramente lógicos/visuales
    print("[MAIN] Instanciando módulos de procesamiento...")
    
    planner = Planner(event_bus)
    sensory = SensoryModule("Sensory", event_bus, shared_sensor_stream, data_task_bus, shared_data)
    # HRI recibe la api_key como pedía el código original
    human_interaction = HRI("HRI", event_bus, shared_sensor_stream, api_key, data_task_bus, shared_data)
    data_manager = DataModule("Data", event_bus, data_task_bus, shared_data)

    # Agregamos los módulos al Planner para que pueda orquestarlos
    planner.append_modules([sensory, human_interaction, data_manager])

    # Iniciamos los hilos de los módulos
    print("[MAIN] Arrancando hilos paralelos...")
    planner.start()
    sensory.start()
    human_interaction.start()
    data_manager.start()

    print("[MAIN] Sistema multimedia y conversacional listo. Cart-ON en marcha.")

    # Bucle principal que mantiene vivo el proceso y supervisa el Planner
    try:
        while planner.running: 
            time.sleep(1)
            
        print("\n[MAIN] El Orquestador ha ordenado el apagado")
            
    except KeyboardInterrupt:
        print("\n[MAIN] Apagado manual detectado")
        
    finally:
        print("🧹 [MAIN] Cerrando módulos de forma segura...")
        event_bus.put(Event(type="shutdown", origin="Main"))
        
        try:
            # Esperamos a que los hilos mueran con honor
            planner.join(timeout=2)
            sensory.join(timeout=2)
            human_interaction.join(timeout=2)
            data_manager.join(timeout=2)
            
        except Exception as e:
            print(f"[MAIN] Error durante el apagado: {e}")
            
        print("[MAIN] Apagado todo correctamente. ¡Hasta la próxima!")
        sys.exit(0)

if __name__ == "__main__":
    main()