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
        self.bridge = None

    def run(self):
        rclpy.init()
        self.bridge = ROSBridge()
        
        super().run()
        
        if self.bridge:
            self.bridge.destroy_node()
        rclpy.shutdown()

    def loop(self):
        
        if self.bridge:
            rclpy.spin_once(
                self.bridge,
                timeout_sec=0
            )

            if self.bridge.latest_scan:

                self.shared_data["scan"] = (
                    self.bridge.latest_scan
                )

            if self.bridge.latest_map:

                self.shared_data["map"] = (
                    self.bridge.latest_map
                )