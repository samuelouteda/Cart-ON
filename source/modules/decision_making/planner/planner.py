from core.base_module import BaseModule
from core.event import Event


class Planner(BaseModule):

    def handle_event(self, event):

        if event.type == "voice_command":

            data = event.data

            intent = data["intent"]

            if intent == "add":

                self.publish_event(
                    Event(
                        type="add_item",
                        data={
                            "item": data["item"],
                            "quantity": data["quantity"]
                        },
                        source=self.name
                    )
                )

                self.publish_event(
                    Event(
                        type="speak",
                        data=f"Añadido {data['item']}"
                    )
                )