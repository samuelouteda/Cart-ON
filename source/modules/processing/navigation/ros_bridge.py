import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import QoSProfile, qos_profile_sensor_data, ReliabilityPolicy, DurabilityPolicy

class ROSBridge(Node):

    def __init__(self):
        super().__init__("carton_bridge")
        self.latest_scan = None
        self.latest_map = None

        self.create_subscription(
            LaserScan,
            "/scan",
            self.scan_callback,
            qos_profile_sensor_data
        )

        perfil_qos_mapa = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )
        self.create_subscription(
            OccupancyGrid,
            "/map",
            self.map_callback,
            perfil_qos_mapa
        )

    def scan_callback(self, msg):
        self.latest_scan = msg

    def map_callback(self, msg):
        self.latest_map = msg
        print(f"[ROSBridge] Mapa rebut: {msg.info.width} x {msg.info.height}")