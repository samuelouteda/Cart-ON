from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
import time


class Navigation(BaseModule):

    def __init__(self, name, event_bus, shared_sensor_stream, data_task_bus, shared_data):
        super().__init__(name, event_bus)
        self.sensor_stream = shared_sensor_stream

        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        
        self.nav_state = "idle"
        self.target_item = None
        self.nav_start_time = 0

    def handle_task(self, task):

        if task.type == "navigate_to_item":

            self.target_item = task.data['item']
            self.nav_state = "calculating"
            self.nav_start_time = time.time()
            print(f"{INDENT_OUTPUT}[{self.name}] Calculating path to \"{self.target_item}\"...")

    def loop(self):
        if self.nav_state == "calculating":
            if time.time() - self.nav_start_time >= 0.2:
                print(f"{INDENT_OUTPUT}[{self.name}] Navigating to \"{self.target_item}\"")
                self.nav_state = "navigating"
                self.nav_start_time = time.time()
        elif self.nav_state == "navigating":
            if time.time() - self.nav_start_time >= 2.0:
                self.publish_event(
                    Event(
                        type="navigation_complete",
                        data=self.target_item,
                        origin=self.name
                    )
                )
                self.nav_state = "idle"
                self.target_item = None