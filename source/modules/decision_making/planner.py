from core.base_module import BaseModule
from core.task import Task

class Planner(BaseModule):

    def __init__(self, event_bus):
        super().__init__("Planner", event_bus)
        self.modules = {}
    
    def append_modules(self, modules):
         print(f"[{self.name}] Appending modules...")
         for m in modules:
              if m not in self.modules:
                   self.modules[m.name] = m

    def handle_event(self, event):
        print(f"[{self.name}] Event received: {event.type} from {event.origin}")
        if event.type == "voice_command":
                item = event.data['item']
                print(f"[{self.name}] User requested: {item}")
                intent = event.data['intent']

                if intent == "add":
                    # Tarea: Añadir item a Data Manager
                    data_task = Task(type="add_item", data={"item": item, "quantity": event.data['quantity']})
                    self.modules["Data"].add_task(data_task)
                    print(f"[{self.name}] Task sent to Data Manager: {data_task.type}")

                    # Tarea: Navegar hacia el item
                    nav_task = Task(type="navigate_to_item", data={"item": item})
                    self.modules["Navigation"].add_task(nav_task)
                    print(f"[{self.name}] Task sent to Navigation: {nav_task.type}")
                    
                    # NUEVO: Tarea visual -> Robot feliz por entender la orden
                    self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "feliz"}))

                elif intent == "delete":
                    data_task = Task(type="delete_item", data={"item": item, "quantity": event.data['quantity']})
                    self.modules["Data"].add_task(data_task)
                    print(f"[{self.name}] Task sent to Data Manager: {data_task.type}")
                    
                    # NUEVO: Tarea visual -> Robot feliz por entender la orden
                    self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "feliz"}))

                elif intent == "read":
                    pass
                    # Podrías poner otra emoción aquí si quisieras
                
                elif intent == "clear":
                    data_task = Task(type="clear_list")
                    self.modules["Data"].add_task(data_task)
                    print(f"[{self.name}] Task sent to Data Manager: {data_task.type}")
                    self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "feliz"}))
        
        elif event.type == "critical_obstacle":
             print(f"[{self.name}] Emergency stop")
             # NUEVO: Cara de alerta/enfado si el robot se choca o hay peligro
             self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "enfadado"}))

    def loop(self):
        while not self.event_queue.empty():
            event = self.event_queue.get()
            self.handle_event(event)

    def run(self):
        print(f"[{self.name}] Started.")
        print(f"[{self.name}] Brain Online. Waiting for events...")
        while self.running:
            self.loop()