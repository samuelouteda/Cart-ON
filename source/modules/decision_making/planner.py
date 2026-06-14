from queue import Empty
from core.base_module import BaseModule
from core.task import Task
from core.event import Event
import time

class Planner(BaseModule):

    def __init__(self, event_bus):
        super().__init__("Planner", event_bus)
        self.modules = {}
        self.fase_actual = "fase_2_interaccion"
    
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
        # FLUJO CONVERSACIONAL (HRI -> CLOUD)
        # =======================================================
        elif type == "VOICE_DETECTED":
            print(f"[{self.name}] Human said: '{data}'")
            if "HRI" in self.modules:
                print(f"[{self.name}] Sending Task to HRI: SEND_TO_CLOUD (voice only)")
                self.modules["HRI"].add_task(Task(type="SEND_TO_CLOUD", data=data))

        elif type == "CLOUD_RESPONSE":
            print(f"[{self.name}] Processing data returned by Cart-ON API.")
            
            if isinstance(data, dict):
                nuevo_estado = data.get("estado_actual")
                if nuevo_estado and nuevo_estado != self.fase_actual:
                    print(f"[{self.name}] Phase transition: {self.fase_actual} -> {nuevo_estado}")
                    self.fase_actual = nuevo_estado

                # 1. Sincronización de lista de la compra
                lista_compra = data.get("lista_compra")
                print(f"[{self.name}] Shopping list received: {lista_compra}")
                if isinstance(lista_compra, dict) and "Data" in self.modules:
                    print(f"[{self.name}] Synchronizing local shopping list from Cloud.")
                    self.modules["Data"].add_task(Task(type="sync_shopping_list", data=lista_compra))

                # 2. Ejecutar habla y pantalla (Multimedia)
                if "HRI" in self.modules:
                    self.modules["HRI"].add_task(Task(type="SPEAK", data=data))

                # 3. Interceptar orden de apagado del asistente
                accion = str(data.get("accion_fisica", "NINGUNA")).upper()
                comando = str(data.get("comando_robot", "NINGUNA")).upper()

                if accion == "SHUTDOWN" or comando == "SHUTDOWN":
                    print(f"[{self.name}] 💀 Qwen ha ordenado el APAGADO del sistema. Ejecutando...")
                    self.event_queue.put(Event(type="shutdown", origin="Cloud"))
                    return

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

    def run(self):
        print(f"[{self.name}] Started.")
        print(f"[{self.name}] Brain Online. Waiting for events...")
        
        if "HRI" in self.modules:
            self.modules["HRI"].add_task(
                Task(
                    type="SPEAK",
                    data={"texto": "Sistema multimedia en línea. Esperando instrucciones."}
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