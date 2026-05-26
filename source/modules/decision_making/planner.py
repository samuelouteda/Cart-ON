from core.base_module import BaseModule
from core.task import Task

class Planner(BaseModule):

    def __init__(self, event_bus):
        super().__init__("Planner", event_bus)
        self.modules = {}
    
    def append_modules(self, modules):
         print(f"[{self.name}] Appending modules...")
         for m in modules:
              if m.name not in self.modules:
                   self.modules[m.name] = m

    def handle_event(self, event):
        print(f"[{self.name}] Event received: {event.type} from {event.origin}")
        
        # ==========================================
        # 1. ÓRDENES DE VOZ (Desde HRI/Gemini)
        # ==========================================
        if event.type == "voice_command":
            item = event.data.get('item')
            quantity = event.data.get('quantity', 1)
            intent = event.data.get('intent')
            
            print(f"[{self.name}] User requested intent: {intent}, item: {item}")

            if intent == "add" and item:
                # 1. Añadir a la lista local (JSON)
                data_task = Task(type="add_item", data={"item": item, "quantity": quantity})
                self.modules["Data"].add_task(data_task)
                print(f"[{self.name}] Task sent to Data Manager: {data_task.type}")
                
                # 2. Feedback visual y de voz
                self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "feliz"}))
                self.modules["HRI"].add_task(Task(type="speak", data={"text": f"Anotado. Buscando {item} en el supermercado."}))

                # 3. NUEVO: Pedir a Cloud SQL dónde está ese producto físicamente
                sql_task = Task(type="request_product_location", data={"item": item})
                self.modules["Data"].add_task(sql_task)
                print(f"[{self.name}] Task sent to Data Manager: {sql_task.type}")

            elif intent == "delete" and item:
                data_task = Task(type="delete_item", data={"item": item, "quantity": quantity})
                self.modules["Data"].add_task(data_task)
                print(f"[{self.name}] Task sent to Data Manager: {data_task.type}")
                
                self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "feliz"}))
                self.modules["HRI"].add_task(Task(type="speak", data={"text": f"He quitado {item} de la lista."}))

            elif intent == "read":
                pass # Aquí podrías añadir lógica para leer la lista en voz alta
            
            elif intent == "clear":
                data_task = Task(type="clear_list", data={})
                self.modules["Data"].add_task(data_task)
                print(f"[{self.name}] Task sent to Data Manager: {data_task.type}")
                
                self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "feliz"}))
                self.modules["HRI"].add_task(Task(type="speak", data={"text": "He vaciado toda tu lista de la compra."}))

        # ==========================================
        # 2. RESPUESTAS DE CLOUD SQL (Desde Data)
        # ==========================================
        elif event.type == "product_location_found":
            nombre = event.data.get("nombre_pantalla")
            pasillo = event.data.get("pasillo")
            coord_x = event.data.get("coordenada_x")
            coord_y = event.data.get("coordenada_y")

            # 1. Avisar por voz de a dónde vamos
            self.modules["HRI"].add_task(Task(type="speak", data={"text": f"El producto {nombre} está en el {pasillo}. Sígueme."}))
            
            # 2. Mandar las coordenadas físicas a los motores
            nav_task = Task(type="navigate_to", data={"x": coord_x, "y": coord_y})
            self.modules["Navigation"].add_task(nav_task)
            print(f"[{self.name}] Task sent to Navigation: Navigating to X:{coord_x}, Y:{coord_y}")

        elif event.type == "product_location_error":
            # Si SQL no lo encuentra, pedimos disculpas
            self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "confuso"}))
            self.modules["HRI"].add_task(Task(type="speak", data={"text": "Lo siento, no tenemos ese producto en nuestro inventario actual."}))

        # ==========================================
        # 3. SEGURIDAD Y NAVEGACIÓN (Desde Sensor)
        # ==========================================
        elif event.type == "critical_obstacle":
            print(f"[{self.name}] Emergency stop")
            # Parada de emergencia a los motores
            self.modules["Navigation"].add_task(Task(type="emergency_stop", data={}))
            # Feedback interactivo
            self.modules["HRI"].add_task(Task(type="set_emotion", data={"emotion": "enfadado"}))
            self.modules["HRI"].add_task(Task(type="speak", data={"text": "¡Cuidado! Obstáculo detectado."}))

    def loop(self):
        while not self.event_queue.empty():
            event = self.event_queue.get()
            self.handle_event(event)

    def run(self):
        print(f"[{self.name}] Started.")
        print(f"[{self.name}] Brain Online. Waiting for events...")
        while self.running:
            self.loop()