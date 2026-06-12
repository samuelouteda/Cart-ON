from queue import Queue, Empty
from threading import Thread
from time import sleep
from core.constants import INDENT_OUTPUT


class BaseModule(Thread):

    def __init__(self, name, event_queue, shared_task_queue=None):
        super().__init__(daemon=True)

        self.name = name

        # Event queue to talk to Planner
        self.event_queue = event_queue 

        # Task queue to receive tasks, either from the Planner or other modules
        if shared_task_queue is None:
            self.task_queue = Queue()
        else:
            self.task_queue = shared_task_queue

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

    def on_shutdown(self):
        """Sobrescribir en submodulos para tareas de limpieza (cerrar archivos, puertos, etc.)"""
        pass

    def run(self):
        indentation = "" if self.name == "Planner" else INDENT_OUTPUT
        print(f"{indentation}[{self.name}] Started.")
        while self.running:

            try:
                task = self.task_queue.get_nowait()

                if hasattr(task, 'type') and task.type == "shutdown":
                    self.running = False
                    break
                self.handle_task(task)

            except Empty:
                pass

            if self.running:
                self.loop()
                sleep(0.01)

        self.on_shutdown()
        print(f"{indentation}[{self.name}] Stopped cleanly.")