import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from nav_msgs.msg import Odometry

import time
import threading
from rplidar import RPLidar  # <--- Fem servir la llibreria de Python directe

class ROSBridge(Node):

    def __init__(self):
        super().__init__("carton_bridge")

        self.latest_scan = None
        self.latest_map = None

        # 1. Subscripcions i Publicadors normals
        self.create_subscription(LaserScan, "/scan", self.scan_callback, 10)
        self.create_subscription(OccupancyGrid, "/map", self.map_callback, 10)
        self.odom_pub = self.create_publisher(Odometry, "/odom", 10)

        # 2. Control directe del Maquinari del LiDAR C1
        self.PORT_NAME = '/dev/ttyUSB0'
        self.BAUDRATE = 460800
        self.lidar = None
        self.is_running = False
        
        self.init_hardware_lidar()

        # 3. Fil dedicat per buidar el buffer a tota velocitat
        if self.lidar:
            self.is_running = True
            self.lidar_thread = threading.Thread(target=self._lidar_worker, daemon=True)
            self.lidar_thread.start()

    def init_hardware_lidar(self):
        try:
            print("[ROSBridge] Inicialitzant el LiDAR RPLIDAR C1 per USB...")
            self.lidar = RPLidar(self.PORT_NAME, baudrate=self.BAUDRATE)
            self.lidar.stop()
            time.sleep(0.2)
            self.lidar.clean_input()
            
            print("[ROSBridge] Engegant el motor del LiDAR C1...")
            self.lidar.start_motor()
            time.sleep(1.5)  # Temps perquè agafi revolucions
            print("[ROSBridge] LiDAR C1 girant i preparat.")
        except Exception as e:
            print(f"[ROSBridge] ERROR en obrir el LiDAR: {e}")
            self.lidar = None

    def _lidar_worker(self):
        """Aquest bucle corre en segon pla absorbint els punts del làser"""
        # Posem un buffer de 3000 perquè absorbeixi les ràfegues del C1
        iterator = self.lidar.iter_scans(max_buf_meas=3000)
        while self.is_running and rclpy.ok():
            try:
                scan = next(iterator)
                # Simulem que ens arriba un LaserScan (Guarda les dades vives)
                # Així el teu loop() de ros_module.py les veurà al shared_data
                self.latest_scan = scan 
                print(f"[ROSBridge] ¡Dades vives! Capturats {len(scan)} punts del làser.", flush=True)
            except StopIteration:
                if self.lidar: iterator = self.lidar.iter_scans(max_buf_meas=3000)
            except Exception as e:
                time.sleep(0.001)

    def scan_callback(self, msg):
        # Aquest callback s'activarà quan slam_toolbox o algú altre publiqui a ROS
        pass

    def map_callback(self, msg):
        self.latest_map = msg
        print(f"[ROSBridge] Map recibido: {msg.info.width} x {msg.info.height}")