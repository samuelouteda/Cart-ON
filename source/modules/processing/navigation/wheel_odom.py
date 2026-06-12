import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
import tf2_ros

TICKS_PER_REV = 2000
WHEEL_RADIUS = 0.0725
WHEELBASE = 0.38
METRES_PER_TICK = (2 * math.pi * WHEEL_RADIUS) / TICKS_PER_REV

class WheelOdom(Node):

    def __init__(self):
        super().__init__("wheel_odom")
        self.odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_left = None
        self.last_right = None
        self._encoders_received = False

        # Timer que publica odom zero fins que arribin encoders reals
        self.create_timer(0.1, self._publish_zero_until_encoders)

    def _publish_zero_until_encoders(self):
        if not self._encoders_received:
            self._publish(self.get_clock().now().to_msg())

    def update_encoders(self, left_ticks, right_ticks):
        self._encoders_received = True
        if self.last_left is None:
            self.last_left = left_ticks
            self.last_right = right_ticks
            return

        delta_left  = (left_ticks  - self.last_left)  * METRES_PER_TICK
        delta_right = (right_ticks - self.last_right) * METRES_PER_TICK
        self.last_left  = left_ticks
        self.last_right = right_ticks

        delta_dist  = (delta_left + delta_right) / 2.0
        delta_theta = (delta_right - delta_left) / WHEELBASE

        self.x     += delta_dist * math.cos(self.theta + delta_theta / 2.0)
        self.y     += delta_dist * math.sin(self.theta + delta_theta / 2.0)
        self.theta += delta_theta

        self._publish(self.get_clock().now().to_msg())

    def _publish(self, stamp):
        qz = math.sin(self.theta / 2.0)
        qw = math.cos(self.theta / 2.0)

        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = "odom"
        t.child_frame_id = "base_link"
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        self.odom_pub.publish(odom)

    def stop(self):
        pass