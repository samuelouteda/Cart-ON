from queue import Queue, Empty
from threading import Thread
from time import sleep


class BaseModule(Thread):

    def __init__(self, name, event_bus):
        super().__init__(daemon=True)

        self.name = name
        self.event_bus = event_bus

        self.task_queue = Queue()

        self.running = True

    def add_task(self, task):
        self.task_queue.put(task)

    def publish_event(self, event):
        self.event_bus.publish(event)

    def process_task(self, task):
        pass

    def loop(self):
        pass

    def run(self):

        while self.running:

            try:
                task = self.task_queue.get_nowait()
                self.process_task(task)

            except Empty:
                pass

            self.loop()

            sleep(0.01)