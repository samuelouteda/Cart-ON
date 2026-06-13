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

# Importamos el Orquestador y las estructuras core
from core.event import Event
from core.task import Task
from modules.decision_making.planner import Planner

# Importamos los Módulos del Robot
from modules.processing.navigation.navigation import Navigation
from modules.sensor.sensor import SensoryModule
from modules.processing.HRI.HRI import HRI
from modules.processing.data.data_manager import DataModule

# Importamos la Capa de Actuación (Solo se usarán si estamos en Linux)
if linux_mode:
    from modules.actuation.wheel_firm import WheelFirm
    from modules.processing.navigation.wheel_odom import WheelOdom

def main():
    print("[MAIN] Iniciando Cart-ON...")
    if linux_mode:
        print("[MAIN] Modo Linux. Hardware y ROS activados.")
    else:
        print("[MAIN] Modo Simulación. Hardware físico deshabilitado.")

    # Inicialización de colas y estructuras compartidas
    event_bus = Queue()
    data_task_bus = Queue()
    shared_sensor_stream = {}
    shared_data = {}

    load_dotenv()
    api_key = os.getenv("API_KEY")

    if not api_key:
        print("[MAIN] Error: Falta la API_KEY en el archivo .env")
        exit()

    # Inicialización del hardware físico (solo en Linux)
    wheel_firm = None
    if linux_mode:
        print("[MAIN] Conectando con Arduino por Serial...")
        try:
            wheel_firm = WheelFirm(port="/dev/ttyACM0", baud=115200)
            shared_data["wheel_firm"] = wheel_firm 

            wheel_odom = WheelOdom()
            wheel_firm.set_odom_node(wheel_odom)
            shared_data["odom"] = wheel_odom
            print("[MAIN] Odometría vinculada a los encoders.")
            
            time.sleep(2) # Tiempo para que el Arduino respire tras abrir el puerto
            
            if not wheel_firm.is_connected():
                print("[MAIN] ADVERTENCIA: Arduino no conectado. Los motores no funcionarán.")
        except Exception as e:
            print(f"[MAIN] Problema inicializando hardware físico: {e}")

    # Instanciación de módulos de procesamiento
    print("[MAIN] Instanciando módulos de procesamiento...")
    
    planner = Planner(event_bus)
    navigation = Navigation("Navigation", event_bus, shared_sensor_stream, data_task_bus, shared_data)
    sensory = SensoryModule("Sensory", event_bus, shared_sensor_stream, data_task_bus, shared_data)
    # HRI recibe la api_key como pedía el código original
    human_interaction = HRI("HRI", event_bus, shared_sensor_stream, api_key, data_task_bus, shared_data)
    data_manager = DataModule("Data", event_bus, data_task_bus, shared_data)

    # Agregamos los módulos al Planner para que pueda orquestarlos
    planner.append_modules([navigation, sensory, human_interaction, data_manager])

    if linux_mode:
        try:
            ros_module = ROSModule("ROS", event_bus, shared_data)
            planner.append_single_module(ros_module)
        except Exception as e:
            print(f"[MAIN] Error iniciando el módulo ROS: {e}")

    # Iniciamos los hilos de los módulos
    print("[MAIN] Arrancando hilos paralelos...")
    planner.start()
    navigation.start()
    sensory.start()
    human_interaction.start()
    data_manager.start()

    if linux_mode and 'ros_module' in locals():
        ros_module.start()

    print("[MAIN] Sistema todo listo. Cart-ON en marcha.")

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
            navigation.join(timeout=2)
            sensory.join(timeout=2)
            human_interaction.join(timeout=2)
            data_manager.join(timeout=2)

            # Apagado del Hardware Físico
            if linux_mode:
                print("[MAIN] Apagando ROS...")
                if wheel_firm:
                    wheel_firm.close()
                if 'ros_module' in locals():
                    ros_module.join(timeout=2)
                rclpy.shutdown()
                
        except Exception as e:
            print(f"[MAIN] Error durante el apagado: {e}")
            
        print("[MAIN] Apagado todo correctamente.")
        sys.exit(0)

if __name__ == "__main__":
    main()