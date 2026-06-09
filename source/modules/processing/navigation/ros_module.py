import rclpy
import subprocess
import time
import os
from rclpy.executors import SingleThreadedExecutor
from core.base_module import BaseModule
from .ros_bridge import ROSBridge

class ROSModule(BaseModule):

    def __init__(self, name, event_bus, shared_data):
        super().__init__(name, event_bus)
        self.shared_data = shared_data
        self.bridge = None
        self.executor = None
        
        # Processos de ROS2
        self.lidar_process = None
        self.slam_process = None
        
        # Configuració del comptador de mapes
        self.scan_counter = 0
        self.MAX_SCANS = 100  # <--- Canvia aquest número pel llibre de punts/scans que vulguis recollir
        self.map_saved = False

    def run(self):
        print(f"[{self.name}] 1. Engegant node físic del LiDAR C1...")
        self.lidar_process = subprocess.Popen([
            "ros2", "run", "sllidar_ros2", "sllidar_node",
            "--ros-args", "-p", "serial_port:=/dev/ttyUSB1", "-p", "baud_rate:=460800"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Donem 2 segons perquè el LiDAR arrenqui abans de demanar-li el SLAM
        time.sleep(2)

        print(f"[{self.name}] 2. Engegant el paquet slam_toolbox...")
        # Nota: Fem servir el llançament síncron online estàndard de slam_toolbox
        self.lidar_process = subprocess.Popen([
            "ros2", "run", "sllidar_ros2", "sllidar_node",
            "--ros-args", "-p", "serial_port:=/dev/ttyUSB1", "-p", "baud_rate:=460800"  # <--- Canviat a ttyUSB1
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Arrenquem el pont de Python cap a ROS2
        self.bridge = ROSBridge()
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.bridge)
        
        super().run()

    def loop(self):
        if self.bridge and self.executor and not self.map_saved:
            self.executor.spin_once(timeout_sec=0.05)

            # Si el bridge ha rebut dades noves del làser
            if self.bridge.latest_scan:
                self.shared_data["scan"] = self.bridge.latest_scan
                self.scan_counter += 1
                print(f"[{self.name}] Scan rebut ({self.scan_counter}/{self.MAX_SCANS})")
                
                # Resetejem la marca de scan capturat al bridge per esperar el següent
                self.bridge.latest_scan = None 

            # QUAN ARRIBEM AL NÚMERO X DE PUNTS -> GENEREM I GUARDEM EL MAPA
            if self.scan_counter >= self.MAX_SCANS:
                self.guardar_mapa_i_tancar()

    def guardar_mapa_i_tancar(self):
        print(f"[{self.name}] target de {self.MAX_SCANS} scans assolit! Generant mapa...")
        self.map_saved = True
        
        # Definim on es guardarà el mapa (a la teva carpeta source/maps)
        # Recomano fer servir la ruta absoluta del teu sistema
        ruta_mapa = os.path.expanduser("~/Cart-ON/source/maps/mapa_carton")
        
        print(f"[{self.name}] Executant nav2_map_server per salvar el mapa a: {ruta_mapa}")
        
        # Comanda oficial de ROS2 per congelar el mapa actual del slam_toolbox
        subprocess.run([
            "ros2", "run", "nav2_map_server", "map_saver_cli", "-f", ruta_mapa
        ])
        
        print(f"[{self.name}] Mapa guardat correctament! Aturant sistemes...")
        self.shutdown_nodes()

    def shutdown_nodes(self):
        # Desconnectem ROS2
        if self.bridge:
            self.executor.remove_node(self.bridge)
            self.bridge.destroy_node()
            
        # Matem els processos de la terminal per deixar el sistema net
        if self.slam_process:
            self.slam_process.terminate()
            self.slam_process.wait()
        if self.lidar_process:
            self.lidar_process.terminate()
            self.lidar_process.wait()
            
        print(f"[{self.name}] Tot apagat de manera neta. Procés finalitzat.")
        exit(0) # Tanquem el main.py automàticament