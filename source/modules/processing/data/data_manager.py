from core.base_module import BaseModule
from core.event import Event
from modules.processing.data.sql_manager import CloudSQLManager
import json
import os

class DataModule(BaseModule):
    """
    Layer 2: Data Manager. 
    Maneja el archivo JSON local (Lista de la compra) y la BBDD Cloud SQL (Mapa del súper).
    """
    _shopping_file = "shopping_list.json"

    def __init__(self, name, event_bus):
        super().__init__(name, event_bus)
        
        # 1. Cargamos la lista local del usuario
        self.shopping_list = self.load_list()
        print(f"[{self.name}] Lista de la compra local cargada: {self.shopping_list}")
        
        # 2. Conectamos con el cerebro de Google Cloud SQL
        print(f"[{self.name}] Conectando con Google Cloud SQL...")
        self.sql_db = CloudSQLManager()

    # --- LÓGICA LOCAL (Lista de la compra) ---
    def load_list(self):
        if os.path.exists(self._shopping_file):
            with open(self._shopping_file, "r", encoding="utf-8") as file:
                return json.load(file)
        return {}
    
    def save_list(self):
        with open(self._shopping_file, "w", encoding="utf-8") as file:
            json.dump(self.shopping_list, file, ensure_ascii=False, indent=4)
        print(f"[{self.name}] Lista guardada en disco.")

    # --- INTERCEPTOR DE TAREAS (Eventos del Bus) ---
    def handle_task(self, task):
        # 1. Tareas de la Lista Local
        if task.type == "add_item":
            item = task.data["item"]
            quantity = task.data["quantity"]
            if item:
                self.shopping_list[item] = self.shopping_list.get(item, 0) + quantity
                self.save_list() # Ahora sí se guarda en el archivo
            
        elif task.type == "delete_item":
            item = task.data["item"]
            if item in self.shopping_list:
                del self.shopping_list[item]
                self.save_list()

        elif task.type == "clear_list":
            self.shopping_list = {}
            self.save_list()

        # 2. Tareas Cloud (Buscar en el Súper)
        elif task.type == "request_product_location":
            item_solicitado = task.data.get("item")
            print(f"[{self.name}] Buscando coordenadas de '{item_solicitado}' en Cloud SQL...")
            
            resultado = self.sql_db.buscar_producto(item_solicitado)
            
            if resultado:
                print(f"[{self.name}] Encontrado: {resultado['nombre_pantalla']} en {resultado['pasillo']}.")
                # Avisamos al sistema de que ya sabemos dónde ir
                self.publish_event(
                    Event(
                        type="product_location_found",
                        data=resultado,
                        origin=self.name
                    )
                )
            else:
                print(f"[{self.name}] El producto '{item_solicitado}' no está en la base de datos.")
                self.publish_event(
                    Event(
                        type="product_location_error",
                        data={"item": item_solicitado, "error": "not_found"},
                        origin=self.name
                    )
                )