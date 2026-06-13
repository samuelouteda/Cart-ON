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
            print(f"[{self.name}] Apagando orquestador y notificando a módulos...")
            shutdown_task = Task(
                        type="shutdown"
                )
            for m in self.modules.values():
                m.add_task(shutdown_task)
            self.running = False
            return

        elif type == "item_added":
            item = data.get('item') if isinstance(data, dict) else data
            print(f"[{self.name}] User requested: {item}")
            if "Navigation" in self.modules:
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
            print(f"[{self.name}] Emergency stop")
            if "Navigation" in self.modules:
                self.modules["Navigation"].add_task(Task(type="STOP_MOTORS"))

        elif type == "VOICE_DETECTED":
            print(f"[{self.name}] Humano dijo: '{data}'")
            if self.fase_actual == "fase_1_escaneo":
                self.frase_pendiente = data
                print(f"[{self.name}] Enviando Task a Sensory: TAKE_PHOTO")
                if "Sensory" in self.modules:
                    self.modules["Sensory"].add_task(Task(type="TAKE_PHOTO"))
            else:
                if "HRI" in self.modules:
                    print(f"[{self.name}] Enviando Task a HRI: SEND_TO_CLOUD (solo voz)")
                    self.modules["HRI"].add_task(Task(type="SEND_TO_CLOUD", data=data))

        elif type == "PHOTO_READY":
            print(f"[{self.name}] Foto lista en el flujo de escaneo.")
            if self.frase_pendiente:
                print(f"[{self.name}] Enviando Task a HRI: SEND_TO_CLOUD (Voz + Foto delegada)")
                if "HRI" in self.modules:
                    self.modules["HRI"].add_task(Task(type="SEND_TO_CLOUD", data=self.frase_pendiente))
                self.frase_pendiente = None

        elif type == "CLOUD_RESPONSE":
            print(f"[{self.name}] Procesando datos devueltos por la API de Cart-ON.")
            if isinstance(data, dict):
                nuevo_estado = data.get("estado_actual")
                if nuevo_estado and nuevo_estado != self.fase_actual:
                    print(f"[{self.name}] Transición de fase: {self.fase_actual} -> {nuevo_estado}")
                    self.fase_actual = nuevo_estado

                lista_compra = data.get("lista_compra")
                print(f"[{self.name}] Lista recibida: {lista_compra}")
                if isinstance(lista_compra, dict) and "Data" in self.modules:
                    print(f"[{self.name}] Sincronizando lista de la compra local desde Cloud.")
                    self.modules["Data"].add_task(Task(type="sync_shopping_list", data=lista_compra))

                if "HRI" in self.modules:
                    self.modules["HRI"].add_task(Task(type="SPEAK", data=data))

                comando = data.get("comando_robot")
                if "Navigation" in self.modules:
                    if comando == "START_SLAM":
                        self.modules["Navigation"].add_task(Task(type="START_MAPPING"))
                    elif comando == "START_NAVIGATION":
                        self.modules["Navigation"].add_task(Task(type="NAVIGATE_TO_TARGET"))
                    elif comando == "STOP_MOTORS":
                        self.modules["Navigation"].add_task(Task(type="STOP_MOTORS"))

    def loop(self):
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get()
                self.handle_event(event)
                self.event_queue.task_done()
            except Empty:
                break
            except Exception as e:
                print(f"[{self.name}] Error procesando evento de la cola: {e}")

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
