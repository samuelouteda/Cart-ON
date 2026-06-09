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
        self.MAX_SCANS = 400  
        self.map_saved = False

    def run(self):
        print(f"[{self.name}] 1. Engegant node físic del LiDAR C1 en /dev/ttyUSB0...")
        self.lidar_process = subprocess.Popen([
            "ros2", "launch", "sllidar_ros2", "sllidar_c1_launch.py",
            "serial_port:=/dev/ttyUSB0"
        ])

        time.sleep(2)

        print(f"[{self.name}] 2. Engegant el paquet slam_toolbox...")
        self.slam_process = subprocess.Popen([
            "ros2", "launch", "slam_toolbox", "online_sync_launch.py"
        ])

        # Arrenquem el pont de Python cap a ROS2
        self.bridge = ROSBridge()
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.bridge)
        
        super().run()

    def loop(self):
        if self.bridge and self.executor and not self.map_saved:
            self.executor.spin_once(timeout_sec=0)

            if self.bridge.latest_scan:
                self.shared_data["scan"] = self.bridge.latest_scan
                self.scan_counter += 1
                if self.scan_counter % 20 == 0:  
                    print(f"[{self.name}] Mapejant... ({self.scan_counter}/{self.MAX_SCANS})")
                self.bridge.latest_scan = None 

            if self.scan_counter >= self.MAX_SCANS:
                self.guardar_mapa_i_tancar()

        time.sleep(0.01)

    def guardar_mapa_i_tancar(self):
            print(f"[{self.name}] Target de {self.MAX_SCANS} scans assolit! Generant mapa...")
            self.map_saved = True
            
            # Donem un parell de segons perquè el SLAM s'estabilitzi abans de demanar el mapa
            time.sleep(2)
            
            ruta_mapa = os.path.expanduser("~/Cart-ON/source/maps/mapa_carton")
            print(f"[{self.name}] Executant nav2_map_server per salvar el mapa a: {ruta_mapa}")
            
            # Executem amb el paràmetre de ROS correcte: save_map_timeout:=10.0
            resultado = subprocess.run([
                "ros2", "run", "nav2_map_server", "map_saver_cli", "-f", ruta_mapa,
                "--ros-args", 
                "-p", "map_subscribe_transient_local:=true", 
                "-p", "save_map_timeout:=10.0"
            ])
            
            if resultado.returncode == 0:
                print(f"[{self.name}] 🥳 ¡MAPA GUARDAT AMB ÈXIT! Aturant sistemes...")
            else:
                print(f"[{self.name}] ❌ ERROR: El map_saver ha fallat de nou.")
                
            self.shutdown_nodes()

    def shutdown_nodes(self):
        if self.bridge:
            self.executor.remove_node(self.bridge)
            self.bridge.destroy_node()
            
        if self.slam_process:
            self.slam_process.terminate()
            self.slam_process.wait()
        if self.lidar_process:
            self.lidar_process.terminate()
            self.lidar_process.wait()
            
        print(f"[{self.name}] Tot apagat de manera neta. Procés finalitzat.")
        exit(0)