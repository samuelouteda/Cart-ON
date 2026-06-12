import rclpy
import subprocess
import time
import os
import sys
import math
from nav_msgs.msg import Odometry
from rclpy.executors import SingleThreadedExecutor
from core.base_module import BaseModule
from .ros_bridge import ROSBridge
from .wheel_odom import WheelOdom
from modules.actuation.wheel_firm import WheelFirm

class ROSModule(BaseModule):

    def __init__(self, name, event_bus, shared_data):
        super().__init__(name, event_bus)
        self.shared_data = shared_data
        self.bridge = None
        self.executor = None
        self.executor_odom = None
        self.lidar_process = None
        self.slam_process = None
        self.tf_laser_process = None
        self.wheel_odom = None
        self.wheel_firm = None
        self.scan_counter = 0
        self.MAX_SCANS = 400
        self.map_saved = False

    def run(self):
        print(f"[{self.name}] 0. Netejant processos residuals...")
        subprocess.run(["pkill", "-f", "slam_toolbox"], capture_output=True)
        subprocess.run(["pkill", "-f", "sllidar_node"], capture_output=True)
        subprocess.run(["pkill", "-f", "static_transform_publisher"], capture_output=True)
        time.sleep(3)

        print(f"[{self.name}] 1. Engegant LiDAR C1...")
        self.lidar_process = subprocess.Popen([
            "ros2", "launch", "sllidar_ros2", "sllidar_c1_launch.py",
            "serial_port:=/dev/ttyUSB0"
        ])
        time.sleep(3)

        print(f"[{self.name}] 2. Publicant TF base_link → laser...")
        self.tf_laser_process = subprocess.Popen([
            "ros2", "run", "tf2_ros", "static_transform_publisher",
            "--x", "0", "--y", "0", "--z", "0.1",
            "--frame-id", "base_link", "--child-frame-id", "laser"
        ])
        time.sleep(1)

        print(f"[{self.name}] 3. Engegant WheelFirm i WheelOdom...")
        self.wheel_firm = WheelFirm(port="/dev/ttyACM0")
        self.wheel_odom = WheelOdom()
        self.wheel_firm.set_odom_node(self.wheel_odom)
        self.shared_data["wheel_firm"] = self.wheel_firm

        self.executor_odom = SingleThreadedExecutor()
        self.executor_odom.add_node(self.wheel_odom)
        fi = time.time() + 2.0
        while time.time() < fi:
            self.executor_odom.spin_once(timeout_sec=0.1)

        print(f"[{self.name}] 4. Engegant slam_toolbox...")
        self.slam_process = subprocess.Popen([
            "ros2", "launch", "slam_toolbox", "online_async_launch.py",
            "slam_params_file:=/home/carton/Cart-ON/source/config/slam_params.yaml"
        ])
        time.sleep(5)

        self.bridge = ROSBridge()
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.bridge)

        super().run()

    def loop(self):
        if self.bridge and self.executor and not self.map_saved:

            self.executor.spin_once(timeout_sec=0)
            if self.executor_odom:
                self.executor_odom.spin_once(timeout_sec=0)

            # Actualitza odom al shared_data
            if self.wheel_odom:
                odom = Odometry()
                odom.pose.pose.position.x = self.wheel_odom.x
                odom.pose.pose.position.y = self.wheel_odom.y
                odom.pose.pose.orientation.z = math.sin(self.wheel_odom.theta / 2.0)
                odom.pose.pose.orientation.w = math.cos(self.wheel_odom.theta / 2.0)
                self.shared_data["odom"] = odom

            # Actualitza scan
            if self.bridge.latest_scan:
                self.shared_data["scan"] = self.bridge.latest_scan
                self.scan_counter += 1
                if self.scan_counter % 20 == 0:
                    print(f"[{self.name}] Mapejant... ({self.scan_counter}/{self.MAX_SCANS})")
                self.bridge.latest_scan = None

            # Actualitza mapa i activa exploració
            if self.bridge.latest_map:
                self.shared_data["map"] = self.bridge.latest_map
                if not self.shared_data.get("exploration_started", False):
                    self.shared_data["exploration_started"] = True
                    self.shared_data["pending_task"] = "start_exploration"
                    print(f"[{self.name}] Primer mapa rebut. Activant exploració...")

            # Guarda mapa quan tenim prous scans
            if self.scan_counter >= self.MAX_SCANS and self.bridge.latest_map:
                self.guardar_mapa_i_tancar()
            elif self.scan_counter >= self.MAX_SCANS:
                if self.scan_counter % 100 == 0:
                    print(f"[{self.name}] ⏳ Esperant /map... (Scans: {self.scan_counter})")
                self.scan_counter += 1

        time.sleep(0.01)

    def guardar_mapa_i_tancar(self):
        print(f"[{self.name}] Guardant mapa...")
        self.map_saved = True
        time.sleep(2)

        ruta_mapa = os.path.expanduser("~/Cart-ON/source/maps/mapa_carton")
        os.makedirs(os.path.dirname(ruta_mapa), exist_ok=True)

        try:
            resultado = subprocess.run([
                "ros2", "service", "call", "/slam_toolbox/save_map",
                "slam_toolbox/srv/SaveMap",
                f"{{name: {{data: '{ruta_mapa}'}}}}"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
               text=True, timeout=15.0)

            if resultado.returncode == 0:
                print(f"[{self.name}] ✅ Mapa guardat a {ruta_mapa}")
            else:
                print(f"[{self.name}] ❌ Error: {resultado.stderr}")
        except subprocess.TimeoutExpired:
            print(f"[{self.name}] ❌ Timeout guardant mapa")
        except Exception as e:
            print(f"[{self.name}] ❌ Error: {e}")

        self.shutdown_nodes()

    def shutdown_nodes(self):
        if self.wheel_firm:
            self.wheel_firm.close()
        if self.bridge:
            try:
                self.executor.remove_node(self.bridge)
                self.bridge.destroy_node()
            except Exception as e:
                print(f"[{self.name}] Error destruint bridge: {e}")
        if self.slam_process:
            self.slam_process.terminate()
            self.slam_process.wait()
        if self.lidar_process:
            self.lidar_process.terminate()
            self.lidar_process.wait()
        if self.tf_laser_process:
            self.tf_laser_process.terminate()
        print(f"[{self.name}] Tot apagat.")
        sys.exit(0)