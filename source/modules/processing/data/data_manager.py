from core.base_module import BaseModule
from core.event import Event

import json
import os

class DataModule(BaseModule):
    """
    Layer 2: Module in charge of reading and storing data on the disk.
    """
    _shopping_file = "shopping_list.json"

    def __init__(self, name, event_bus):

        super().__init__(name, event_bus)

        
        self.shopping_list = self.load_list()
        

    def load_list(self):
        if os.path.exists(self._shopping_file):
            with open(self._shopping_file, "r", encoding="utf-8") as file:
                return json.load(file)
        return {}
    
    def save_list(self):
        with open(self._shopping_file, "w", encoding="utf-8") as file:
            json.dump(self.shopping_list, file, ensure_ascii=False, indent=4)

    def handle_task(self, task):

        if task.type == "add_item":

            item = task.data["item"]
            quantity = task.data["quantity"]
            if item:
                self.shopping_list[item] = self.shopping_list.get(item, 0) + quantity
            
        elif task.type == "delete_item":
            item = task.data["item"]
            if item in self.shopping_list:
                del self.shopping_list[item]

        elif task.type == "clear_list":

            self.shopping_list = {}