from queue import Queue, Empty
from threading import Thread
from time import sleep
from core.constants import INDENT_OUTPUT


class BaseModule(Thread):

    def __init__(self, name, event_queue):
        super().__init__(daemon=True)

        self.name = name
        self.event_queue = event_queue # Para hablar al Planificador
        self.task_queue = Queue() # Para recibir tareas del Planificador
        self.running = True

    def add_task(self, task):
        self.task_queue.put(task)

    def publish_event(self, event):
        self.event_queue.put(event)

    def handle_task(self, task):
        """
        Sobrescribir esta funcion en cada modulo para manejar comandos especificos
        """
        pass

    def loop(self):
        """
        Sobrescribir esta funcion en cada modulo para personalizar su propio loop
        """
        pass

    def run(self):
        indentation = "" if self.name == "Planner" else INDENT_OUTPUT
        print(f"{indentation}[{self.name}] Started.")
        while self.running:

            try:
                task = self.task_queue.get_nowait()
                self.handle_task(task)

            except Empty:
                pass

            self.loop()

            sleep(0.01)