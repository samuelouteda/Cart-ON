from queue import Empty
from core.base_module import BaseModule
from core.task import Task
import time

class Planner(BaseModule):

    def __init__(self, event_bus):
        super().__init__("Planner", event_bus)
        self.modules = {}
    
    def append_single_module(self, module):
        if module not in self.modules:
            self.modules[module.name] = module

    def append_modules(self, modules):
         print(f"[{self.name}] Appending modules...")
         for m in modules:
              if m not in self.modules:
                   self.modules[m.name] = m

    def handle_event(self, event):
        print(f"[{self.name}] Event received: {event.type} from {event.origin}")

        if event.type == "item_added":
            item = event.data['item']
            print(f"[{self.name}] User requested: {item}")
            self.modules["Navigation"].add_task(
                Task(
                        type="navigate_to_item",
                        data={
                            "item": item,
                        }
                )
            )
            print(f"[{self.name}] Task sent to Navigation: navigate_to_item")

        elif event.type == "item_deleted":
            item = event.data['item']
            print(f"[{self.name}] {item} succesfully deleted.")

        elif event.type == "read_list":
            print(f"[{self.name}] Reading list...")
            
        elif event.type == "list_cleared":
            print(f"[{self.name}] List succesfully cleared.")
        
        elif event.type == "critical_obstacle":
             print(f"[{self.name}] Emergency stop")

    def loop(self):
        while not self.event_queue.empty():
            event = self.event_queue.get()
            self.handle_event(event)

    def run(self):
        print(f"[{self.name}] Started.")
        print(f"[{self.name}] Brain Online. Waiting for events...")
        
        if "HRI" in self.modules:
            self.modules["HRI"].add_task(
                    Task(
                            type="speak",
                            data="Cerebro en línea. Esperando por eventos..."
                    )
                )

        while self.running:
            try:
                task = self.task_queue.get_nowait()
                self.handle_task(task)
            except Empty:
                pass

            self.loop()
            time.sleep(0.01)