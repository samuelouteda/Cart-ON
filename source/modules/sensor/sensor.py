from core.base_module import BaseModule
from core.event import Event
from queue import Empty
from time import sleep
import speech_recognition as sr
from core.constants import INDENT_OUTPUT

class SensoryModule(BaseModule):
    """
    Layer 3: Continuously polls hardware and 'publishes' data.
    """
    def __init__(self, name, event_queue, shared_sensor_stream, data_task_bus, shared_data):
        super().__init__(name, event_queue)
        self.data_stream = shared_sensor_stream
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        
    def capture_audio(self):
        # modulo hardware que captura la entrada de audio del entorno
        with self.microphone as source:
            try:
                # graba bloques de audio y se detiene si hay silencio
                audio_data = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                return audio_data
            except sr.WaitTimeoutError:
                return None
            except Exception:
                return None

    def loop(self):
        self.data_stream['audio'] = self.capture_audio()
    

    def run(self):

        self.data_stream['audio'] = None
        self.data_stream['distance'] = 5

        # calibramos un segundo completo para evitar falsos positivos de ruido
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        self.publish_event(
                Event(
                    type="distance_data",
                    data=42,
                    origin=self.name
                )
            )


        self.publish_event(
            Event(
                type="critical_obstacle",
                data=self.data_stream['distance'],
                origin=self.name
            )
        )

        while self.running:
            try:
                task = self.task_queue.get_nowait()
                if hasattr(task, 'type') and task.type == "shutdown":
                    self.running = False
                    break
            except Empty:
                pass

            if self.running:
                self.loop()
                sleep(0.01)

        print(f"{INDENT_OUTPUT}[{self.name}] Stopped cleanly.")