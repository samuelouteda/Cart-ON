from queue import Empty
from core.base_module import BaseModule
from core.task import Task
import time

class Planner(BaseModule):

    def __init__(self, event_bus):
        super().__init__("Planner", event_bus)
        self.modules = {}

        self.fase_actual = "fase_2_interaccion"
        self.frase_pendiente = None

        self.current_item = None
        self.replan_time = None
    
    def append_single_module(self, module):
        if module.name not in self.modules:
            self.modules[module.name] = module

    def append_modules(self, modules):
         print(f"[{self.name}] Appending modules...")
         for m in modules:
              if m.name not in self.modules:
                   self.modules[m.name] = m
    
    def add_data_task(self, task):
        self.data_task_bus.put(task)

    def handle_event(self, event):
        if isinstance(event, dict):
            type = event.get("type")
            data = event.get("data")
            origin = event.get("origin", "Sistema")
        else:
            type = getattr(event, 'type', None)
            data = getattr(event, 'data', None)
            origin = getattr(event, 'origin', 'Desconocido')

        print(f"[{self.name}] Event received: {type} from {origin}")

        if str(type).lower() == "shutdown":
            print(f"[{self.name}] Shutting down orchestrator and notifying modules....")
            shutdown_task = Task(type="shutdown")
            for m in self.modules.values():
                m.add_task(shutdown_task)
            self.running = False
            return

        # =======================================================
        # ESCANEO DE ESTANTERÍAS
        # =======================================================
        elif type == "SHELF_DETECTED":
            print(f"[{self.name}] Navigator reported shelf. Ordering Sensory to take photo...")
            if "Sensory" in self.modules:
                self.modules["Sensory"].add_task(Task(type="TAKE_INVENTORY_PHOTO"))

        elif type == "PHOTO_DONE":
            print(f"[{self.name}] Sensory finished cloud scanning. Ordering Navigation to resume...")
            if "Navigation" in self.modules:
                self.modules["Navigation"].add_task(Task(type="RESUME_AFTER_PHOTO"))

        elif type == "item_added":
            item = data.get('item') if isinstance(data, dict) else data
            print(f"[{self.name}] User requested: {item}")
            if "Navigation" in self.modules:
                self.current_item = item
                self.modules["Navigation"].add_task(Task(type="navigate_to_item", data={"item": item}))
                print(f"[{self.name}] Task sent to Navigation: navigate_to_item")

        elif type == "item_deleted":
            item = data.get('item') if isinstance(data, dict) else data
            print(f"[{self.name}] {item} successfully deleted.")

        elif type == "read_list":
            print(f"[{self.name}] Reading list...")
            
        elif type == "list_cleared":
            print(f"[{self.name}] List successfully cleared.")
        
        elif type == "critical_obstacle":
            print(f"[{self.name}] Emergency stop triggered.")
            if "Navigation" in self.modules:
                self.modules["Navigation"].add_task(Task(type="STOP_MOTORS"))

                if self.current_item:
                    self.replan_time = time.time() + 3.0
                    print(f"[{self.name}] Replanning to '{self.current_item}' scheduled in 3 seconds...")

        elif type == "VOICE_DETECTED":
            print(f"[{self.name}] Human said: '{data}'")
            if self.fase_actual == "fase_1_escaneo":
                self.frase_pendiente = data
                print(f"[{self.name}] Sending Task to Sensory: TAKE_PHOTO")
                if "Sensory" in self.modules:
                    self.modules["Sensory"].add_task(Task(type="TAKE_PHOTO"))
            else:
                if "HRI" in self.modules:
                    print(f"[{self.name}] Sending Task to HRI: SEND_TO_CLOUD (voice only)")
                    self.modules["HRI"].add_task(Task(type="SEND_TO_CLOUD", data=data))

        elif type == "PHOTO_READY":
            print(f"[{self.name}] Photo ready in human scanning flow.")
            if self.frase_pendiente:
                print(f"[{self.name}] Sending Task to HRI: SEND_TO_CLOUD (Voice + Delegated Photo)")
                if "HRI" in self.modules:
                    self.modules["HRI"].add_task(Task(type="SEND_TO_CLOUD", data=self.frase_pendiente))
                self.frase_pendiente = None

        elif type == "CLOUD_RESPONSE":
            print(f"[{self.name}] Processing data returned by Cart-ON API.")
            if isinstance(data, dict):
                nuevo_estado = data.get("estado_actual")
                if nuevo_estado and nuevo_estado != self.fase_actual:
                    print(f"[{self.name}] Phase transition: {self.fase_actual} -> {nuevo_estado}")
                    self.fase_actual = nuevo_estado

                lista_compra = data.get("lista_compra")
                print(f"[{self.name}] Shopping list received: {lista_compra}")
                if isinstance(lista_compra, dict) and "Data" in self.modules:
                    print(f"[{self.name}] Synchronizing local shopping list from Cloud.")
                    self.modules["Data"].add_task(Task(type="sync_shopping_list", data=lista_compra))

                if "HRI" in self.modules:
                    self.modules["HRI"].add_task(Task(type="SPEAK", data=data))

                # 🚀 NUEVO: Capturamos 'accion_fisica' (conducción multipunto y mapeo)
                accion = data.get("accion_fisica", "NINGUNA")
                comando = data.get("comando_robot") # Por si queda algo legacy

                if "Navigation" in self.modules:
                    if accion == "INICIAR_MAPEO" or comando == "START_SLAM":
                        self.modules["Navigation"].add_task(Task(type="START_MAPPING"))
                    elif accion == "INICIAR_CONDUCCION" or comando == "START_NAVIGATION":
                        # Pasamos los datos enteros (ruta_supermercado, lat, lng, aula)
                        self.modules["Navigation"].add_task(Task(type="START_DRIVING", data=data))
                    elif comando == "STOP_MOTORS":
                        self.modules["Navigation"].add_task(Task(type="STOP_MOTORS"))

    def loop(self):
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get()
                self.handle_event(event)
            except Empty:
                break
            except Exception as e:
                print(f"[{self.name}] Error processing event from queue: {e}")
            finally:
                self.event_queue.task_done()
        
        if self.replan_time and time.time() >= self.replan_time:
            if self.current_item and "Navigation" in self.modules:
                print(f"[{self.name}] Security timeout reached. Recalculating path to: {self.current_item}")
                self.modules["Navigation"].add_task(Task(type="navigate_to_item", data={"item": self.current_item}))
            self.replan_time = None  # Reseteamos el temporizador

    def run(self):
        print(f"[{self.name}] Started.")
        print(f"[{self.name}] Brain Online. Waiting for events...")
        
        if "HRI" in self.modules:
            self.modules["HRI"].add_task(
                    Task(
                            type="SPEAK",
                            data={"texto": "Cerebro en línea. Esperando por eventos..."}
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
            
        print(f"[{self.name}] Stopped cleanly.")