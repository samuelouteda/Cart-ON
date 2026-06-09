import rclpy
from rclpy.executors import SingleThreadedExecutor
from core.base_module import BaseModule
from .ros_bridge import ROSBridge

class ROSModule(BaseModule):

    def __init__(self, name, event_bus, shared_data):
        super().__init__(name, event_bus)
        self.shared_data = shared_data
        self.bridge = None
        self.executor = None

    def run(self):
        self.bridge = ROSBridge()
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.bridge)
        
        super().run()
        
        if self.bridge:
            self.executor.remove_node(self.bridge)
            self.bridge.destroy_node()

    def loop(self):
        if self.bridge and self.executor:
            self.executor.spin_once(timeout_sec=0)

            if self.bridge.latest_scan:
                self.shared_data["scan"] = self.bridge.latest_scan

            if self.bridge.latest_map:
                self.shared_data["map"] = self.bridge.latest_map