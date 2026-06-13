import time
from queue import Queue
import sys

# Importamos el Orquestador y las estructuras core
from core.event import Event
from core.task import Task
from modules.decision_making.planner import Planner

# Importamos los Módulos del Robot
from modules.processing.navigation.navigation import Navigation
from modules.sensor.sensor import SensoryModule
# (Asegúrate de que las rutas de HRI y Data coincidan con tus carpetas)
from modules.processing.HRI import HRI 
from modules.processing.data import Data

# Importamos la Capa de Actuación (Motores y Odometría)
from modules.actuation.wheel_firm import WheelFirm
from modules.processing.navigation.wheel_odom import WheelOdom

def main():
    print("🤖 [MAIN] Iniciando Cart-ON Local OS...")

    # =======================================================
    # 🧠 1. CREAMOS LAS MEMORIAS Y BUSES COMPARTIDOS
    # =======================================================
    event_bus = Queue()               # El bus central donde todos los eventos gritan al Planner
    data_task_bus = {}                # Buzones específicos si hicieran falta
    shared_sensor_stream = {}         # Datos en crudo en tiempo real (distancia, audio, etc.)
    shared_data = {}                  # Memoria global (mapas, hardware, localizaciones)

    # =======================================================
    # ⚙️ 2. INICIALIZAMOS EL HARDWARE FÍSICO (ARDUINO)
    # =======================================================
    print("🔌 [MAIN] Conectando con Arduino por Serial...")
    # ⚠️ Ajusta el puerto a tu Raspberry/Ubuntu (/dev/ttyACM0 o /dev/ttyUSB0)
    wheel_firm = WheelFirm(port="/dev/ttyACM0", baud=115200)
    
    # Inyectamos el firmware en la memoria compartida para que Navigation lo pueda coger
    shared_data["wheel_firm"] = wheel_firm 

    # Vinculamos la odometría a los encoders de las ruedas
    try:
        wheel_odom = WheelOdom()
        wheel_firm.set_odom_node(wheel_odom)
        shared_data["odom"] = wheel_odom
        print("✅ [MAIN] Odometría vinculada a los encoders.")
    except Exception as e:
        print(f"⚠️ [MAIN] Problema inicializando WheelOdom: {e}")

    # Damos 2 segundos para que el Arduino se reinicie tranquilamente tras abrir el puerto Serial
    time.sleep(2)

    if not wheel_firm.is_connected():
        print("🔴 [MAIN] ADVERTENCIA CRÍTICA: Arduino no conectado. Los motores no funcionarán.")

    # =======================================================
    # 🧩 3. INSTANCIAMOS LOS MÓDULOS DE SOFTWARE
    # =======================================================
    print("📦 [MAIN] Instanciando módulos de procesamiento...")
    
    # El Jefe
    planner = Planner(event_bus)
    
    # Los Esclavos
    navigation = Navigation("Navigation", event_bus, shared_sensor_stream, data_task_bus, shared_data)
    sensory = SensoryModule("Sensory", event_bus, shared_sensor_stream, data_task_bus, shared_data)
    hri = HRI("HRI", event_bus, shared_sensor_stream, data_task_bus, shared_data)
    data_module = Data("Data", event_bus, shared_sensor_stream, data_task_bus, shared_data)

    # =======================================================
    # 🔗 4. CONECTAMOS LOS MÓDULOS AL ORQUESTADOR
    # =======================================================
    planner.append_modules([navigation, sensory, hri, data_module])

    # =======================================================
    # 🚀 5. ARRANCAMOS LOS MOTORES DE SOFTWARE (HILOS)
    # =======================================================
    print("🔥 [MAIN] Arrancando hilos paralelos...")
    navigation.start()
    sensory.start()
    hri.start()
    data_module.start()
    
    # El Planner arranca el último para asegurarse de que todos están listos
    planner.start()

    print("✅ [MAIN] SISTEMA CART-ON TOTALMENTE OPERATIVO. Pulsa Ctrl+C para apagar.")

    # =======================================================
    # ♾️ 6. BUCLE INFINITO DE MANTENIMIENTO
    # =======================================================
    try:
        while True:
            # El hilo principal solo se queda dormido manteniendo el programa vivo
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 [MAIN] Apagado manual detectado (Ctrl+C). Iniciando protocolo de parada...")
    
    finally:
        # =======================================================
        # 🧹 7. LIMPIEZA FINAL Y FRENO DE EMERGENCIA FÍSICO
        # =======================================================
        print("🧹 [MAIN] Cerrando módulos de forma segura...")
        # Le gritamos al Planner que apague todo el software
        event_bus.put(Event(type="shutdown", origin="Main"))
        
        # Damos 1.5 segundos para que los hilos terminen sus tareas y mueran en paz
        time.sleep(1.5) 
        
        # PARADA DE SEGURIDAD ABSOLUTA DEL HARDWARE
        print("🛑 [MAIN] Cortando energía a los motores...")
        if wheel_firm:
            wheel_firm.close()
            
        print("🏁 [MAIN] Cart-ON OS apagado correctamente. ¡Hasta la próxima!")
        sys.exit(0)

if __name__ == "__main__":
    main()