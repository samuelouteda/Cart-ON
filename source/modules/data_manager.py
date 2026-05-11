from core.base_module import BaseModule
from core.event import Event

from services.storage_service import (
    load_list,
    save_list
)


class DataModule(BaseModule):

    def __init__(self, name, event_bus):

        super().__init__(name, event_bus)

        self.shopping_list = load_list()

    def handle_event(self, event):

        if event.type == "add_item":

            item = event.data["item"]
            quantity = event.data["quantity"]

            self.shopping_list[item] = (
                self.shopping_list.get(item, 0)
                + quantity
            )

            save_list(self.shopping_list)

        elif event.type == "clear_list":

            self.shopping_list = {}

            save_list(self.shopping_list)