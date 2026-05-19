from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
import time


class Navigation(BaseModule):

    def __init__(self, name, event_bus, shared_sensor_stream):
        super().__init__(name, event_bus)
        self.data_stream = shared_sensor_stream

    def handle_task(self, task):

        if task.type == "navigate_to_item":

            item = task.data['item']

            print(f"{INDENT_OUTPUT}[{self.name}] Calculating path to \"{item}\"...")
            
            time.sleep(0.2)
            print(f"{INDENT_OUTPUT}[{self.name}] Navigating to \"{item}\"")
            time.sleep(2)

            self.publish_event(
                Event(
                    type="navigation_complete",
                    data=item,
                    origin=self.name
                )
            )