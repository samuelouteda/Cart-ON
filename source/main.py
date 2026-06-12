from queue import Queue
from collections import deque as Deque
from dotenv import load_dotenv
import os
import sys
import time

linux_mode = 0
if sys.platform.startswith("linux"):
    linux_mode = 1

if linux_mode:
    import rclpy
    rclpy.init()
    from modules.processing.navigation.ros_module import ROSModule

from modules.decision_making.planner import Planner
from modules.processing.navigation.navigation import Navigation
from modules.processing.HRI.HRI import HRI
from modules.processing.data.data_manager import DataModule
from modules.sensor.sensor import SensoryModule
from core.event import Event

def main():
    # ==================================================================================================
    # Inicializacion de variables ======================================================================
    # ==================================================================================================

    event_bus = Queue()
    data_task_bus = Queue()
    sensor_data = {}
    shared_data = {}

    api_key = ""
    load_dotenv()
    api_key = os.getenv("API_KEY")

    if not api_key:
        print("Error critico: falta la API_KEY (Voz STT/TTS) en el archivo .env")
        exit()

    # ==================================================================================================
    # Instanciacion de modulos =========================================================================
    # ==================================================================================================

    planner = Planner(event_bus)
    navigation = Navigation("Navigation", event_bus, sensor_data, data_task_bus, shared_data)
    sensory = SensoryModule("Sensory", event_bus, sensor_data, data_task_bus, shared_data)
    human_interaction = HRI("HRI", event_bus, sensor_data, api_key, data_task_bus, shared_data)
    data_manager = DataModule("Data", event_bus, data_task_bus, shared_data)

    # ==================================================================================================
    # Acoplamiento de modulos ==========================================================================
    # ==================================================================================================

    planner.append_modules([navigation, sensory, human_interaction, data_manager])

    if linux_mode:
        ros_module = ROSModule("ROS", event_bus, shared_data)
        planner.append_single_module(ros_module)

    # ==================================================================================================
    # Inicio de hilos ==================================================================================
    # ==================================================================================================

    planner.start()
    navigation.start()
    sensory.start()
    human_interaction.start()
    data_manager.start()

    if linux_mode:
        ros_module.start()

    # ==================================================================================================
    # Bucle de vigilancia del hilo principal ===========================================================
    # ==================================================================================================

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        event_bus.put(Event(type="shutdown", origin="Main"))
    
    try:
        planner.join(timeout=2)
        navigation.join(timeout=2)
        sensory.join(timeout=2)
        human_interaction.join(timeout=2)
        data_manager.join(timeout=2)

        if linux_mode:
            ros_module.join(timeout=2)
            rclpy.shutdown()
        
        
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()