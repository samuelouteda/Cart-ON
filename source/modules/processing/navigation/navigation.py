from core.base_module import BaseModule
from core.event import Event


class Navigation(BaseModule):

    def process_task(self, task):

        if task.type == "navigate_to_item":

            item = task.data

            print(f"[Navigation] Navigating to {item}")

            self.publish_event(
                Event(
                    type="navigation_complete",
                    data=item,
                    source=self.name
                )
            )