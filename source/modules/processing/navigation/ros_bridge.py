import rclpy

from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from nav_msgs.msg import Odometry


class ROSBridge(Node):

    def __init__(self):

        super().__init__("carton_bridge")

        self.latest_scan = None
        self.latest_map = None

        self.create_subscription(
            LaserScan,
            "/scan",
            self.scan_callback,
            10
        )

        self.create_subscription(
            OccupancyGrid,
            "/map",
            self.map_callback,
            10
        )

        self.odom_pub = self.create_publisher(
            Odometry,
            "/odom",
            10
        )

    def scan_callback(self,msg):
        self.latest_scan = msg
        print(f"[ROSBridge] LaserScan recibido: {len(msg.ranges)} puntos")
        #print(f"[ROSBridge] {msg.ranges}")

    def map_callback(self,msg):
        self.latest_map = msg
        print(f"[ROSBridge] Map recibido: {msg.info.width} x {msg.info.height}")