from queue import Queue
from collections import deque as Deque
from dotenv import load_dotenv
import os
import sys
import time

# Detectamos si estamos en Linux para decidir si inicializamos ROS y el hardware físico
linux_mode = False
if sys.platform.startswith("linux"):
    linux_mode = True

if linux_mode:
    import rclpy
    rclpy.init()
    from modules.processing.navigation.ros_module import ROSModule
    from modules.processing.navigation.wheel_odom import WheelOdom
    from modules.actuation.wheel_firm import WheelFirm

from modules.decision_making.planner import Planner
from modules.processing.navigation.navigation import Navigation
from modules.processing.HRI.HRI import HRI
from modules.processing.data.data_manager import DataModule
from modules.sensor.sensor import SensoryModule
from core.event import Event

def main():
    print("[MAIN] Starting Cart-ON...")
    if linux_mode:
        print("[MAIN] Linux Mode. Hardware and ROS activated.")
    else:
        print("[MAIN] Simulation Mode. Physical hardware disabled.")

    # ==================================================================================================
    # Inicializacion de variables ======================================================================
    # ==================================================================================================
    event_bus = Queue()
    data_task_bus = Queue()
    sensor_data = {}
    shared_data = {}

    load_dotenv()
    api_key = os.getenv("API_KEY")

    if not api_key:
        print("[MAIN] Critical error: Missing API_KEY (Voice STT/TTS) in the .env file")
        exit()

    # Inicialización del hardware físico (solo en Linux)
    wheel_firm = None
    if linux_mode:
        print("[MAIN] Connecting to Arduino via Serial...")
        try:
            wheel_firm = WheelFirm(port="/dev/ttyACM0", baud=115200)
            shared_data["wheel_firm"] = wheel_firm 

            wheel_odom = WheelOdom()
            wheel_firm.set_odom_node(wheel_odom)
            shared_data["odom"] = wheel_odom
            print("[MAIN] Odometry linked to encoders.")
            
            time.sleep(2) # Tiempo para que el Arduino respire tras abrir el puerto
            
            if not wheel_firm.is_connected():
                print("[MAIN] WARNING: Arduino not connected. Motors will not work.")
        except Exception as e:
            print(f"[MAIN] Problem initializing physical hardware: {e}")

    # ==================================================================================================
    # Instanciacion de modulos =========================================================================
    # ==================================================================================================

    print("[MAIN] Instantiating processing modules...")
    
    planner = Planner(event_bus)
    navigation = Navigation("Navigation", event_bus, sensor_data, data_task_bus, shared_data)
    sensory = SensoryModule("Sensory", event_bus, sensor_data, data_task_bus, shared_data)
    human_interaction = HRI("HRI", event_bus, sensor_data, api_key, data_task_bus, shared_data)
    data_manager = DataModule("Data", event_bus, data_task_bus, shared_data)

    # ==================================================================================================
    # Acoplamiento de modulos ==========================================================================
    # ==================================================================================================

    planner.append_modules([navigation, sensory, human_interaction, data_manager])

    # COMENTADO: Desactivamos ROS/LiDAR temporalmente para probar los comandos de voz
    # if linux_mode:
    #     try:
    #         ros_module = ROSModule("ROS", event_bus, shared_data)
    #         planner.append_single_module(ros_module)
    #     except Exception as e:
    #         print(f"[MAIN] Error starting ROS module: {e}")

    # ==================================================================================================
    # Inicio de hilos ==================================================================================
    # ==================================================================================================

    print("[MAIN] Starting parallel threads...")
    planner.start()
    navigation.start()
    sensory.start()
    human_interaction.start()
    data_manager.start()

    # COMENTADO: No arrancamos el hilo de ROS/LiDAR
    # if linux_mode and 'ros_module' in locals():
    #     ros_module.start()

    print("[MAIN] System ready. Cart-ON running.")

    # ==================================================================================================
    # Bucle de vigilancia del hilo principal ===========================================================
    # ==================================================================================================

    try:
        while planner.running: 
            time.sleep(1)
            
        print("\n[MAIN] The Orchestrator has ordered shutdown.")
            
    except KeyboardInterrupt:
        print("\n[MAIN] Manual shutdown detected.")
        
    finally:
        print("[MAIN] Closing modules safely...")
        event_bus.put(Event(type="shutdown", origin="Main"))
        
        try:
            # Esperamos a que los hilos mueran con honor
            planner.join(timeout=2)
            navigation.join(timeout=2)
            sensory.join(timeout=2)
            human_interaction.join(timeout=2)
            data_manager.join(timeout=2)

            # Apagado del Hardware Fisico
            if linux_mode:
                print("[MAIN] Shutting down ROS...")
                if wheel_firm:
                    wheel_firm.close()
                
                # COMENTADO: No esperamos a que cierre el hilo de ROS porque no se ha abierto
                # if 'ros_module' in locals():
                #     ros_module.join(timeout=2)
                
                rclpy.shutdown()
                
        except Exception as e:
            print(f"[MAIN] Error during shutdown: {e}")
        except KeyboardInterrupt:
            pass
            
        print("[MAIN] System shut down successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
    