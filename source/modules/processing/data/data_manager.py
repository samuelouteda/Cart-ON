from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

import json
import os

class DataModule(BaseModule):
    """
    Layer 2: Module in charge of reading and storing data on the disk.
    """
    _shopping_file = "shopping_list.json"

    def __init__(self, name, event_bus, data_task_bus, shared_data):
        super().__init__(name, event_bus, data_task_bus)
        self.shared_data = shared_data
        self.load_data()

    @property
    def shopping_file_path(self):
        return os.path.abspath(self._shopping_file)
        
    def load_data(self):
        self.shared_data['shopping_list'] = self.load_list()

    def load_list(self):
        if os.path.exists(self._shopping_file):
            with open(self._shopping_file, "r", encoding="utf-8") as file:
                return json.load(file)
        return {}
    
    def save_list(self):
        with open(self._shopping_file, "w", encoding="utf-8") as file:
            json.dump(self.shared_data['shopping_list'], file, ensure_ascii=False, indent=4)

    def on_shutdown(self):
        print(f"{INDENT_OUTPUT}[{self.name}] Saving shopping list on disk before shutting down...")
        self.save_list()
        print(f"{INDENT_OUTPUT}[{self.name}] Shopping list succesfully saved at {self.shopping_file_path}.")

    def handle_task(self, task):
        if task.type == "add_item":
            item = task.data["item"]
            quantity = task.data["quantity"]
            if item:
                self.shared_data['shopping_list'][item] = self.shared_data['shopping_list'].get(item, 0) + quantity
            
        elif task.type == "delete_item":
            item = task.data["item"]
            if item in self.shared_data['shopping_list']:
                del self.shared_data['shopping_list'][item]

        elif task.type == "clear_list":
            self.shared_data['shopping_list'] = {}

        elif task.type == "sync_shopping_list":
            if isinstance(task.data, dict):
                self.shared_data['shopping_list'] = task.data.copy()
                self.save_list()
                print(
                    f"{INDENT_OUTPUT}[{self.name}] Shopping list synced from Cloud and saved at "
                    f"{self.shopping_file_path}: {self.shared_data['shopping_list']}"
                )
            else:
                print(f"{INDENT_OUTPUT}[{self.name}] Ignoring invalid shopping list sync payload: {task.data}")

        elif task.type == "audio_to_speak":
            self.shared_data['audio_to_speak'] = task.data