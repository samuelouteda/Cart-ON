import rclpy

from core.base_module import BaseModule

from .ros_bridge import ROSBridge


class ROSModule(BaseModule):

    def __init__(
        self,
        name,
        event_bus,
        shared_data
    ):

        super().__init__(
            name,
            event_bus
        )

        self.shared_data = shared_data

        rclpy.init()

        self.bridge = ROSBridge()

    def loop(self):

        rclpy.spin_once(
            self.bridge,
            timeout_sec=0.01
        )

        if self.bridge.latest_scan:

            self.shared_data["scan"] = (
                self.bridge.latest_scan
            )

        if self.bridge.latest_map:

            self.shared_data["map"] = (
                self.bridge.latest_map
            )