from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

from queue import Empty
from time import sleep
import time
import speech_recognition as sr
import cv2
import base64
import requests
import threading

class SensoryModule(BaseModule):
    """
    Layer 3: Continuously polls hardware and 'publishes' data.
    Handles both Microphone (Background Thread) and Camera (On-Demand Tasks).
    """
    def __init__(self, name, event_queue, shared_sensor_stream, data_task_bus, shared_data):
        super().__init__(name, event_queue)
        self.data_stream = shared_sensor_stream
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        
        # Vision attributes
        self.cloud_scan_url = "https://cart-on-api-225606614592.europe-west1.run.app/api/v1/escaneo_inventario"
        self.is_scanning = False
        
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

    def _audio_loop(self):
            """Dedicated background loop for microphone processing"""
            print(f"{INDENT_OUTPUT}[{self.name}] Audio listener thread started.")
            while self.running:
                self.data_stream['audio'] = self.capture_audio()
                sleep(0.05)

    def loop(self):
        pass

    def handle_task(self, task):
        if task.type == "shutdown":
            self.running = False
        elif task.type == "TAKE_INVENTORY_PHOTO":
            if not self.is_scanning:
                self.is_scanning = True
                print(f"{INDENT_OUTPUT}[{self.name}] Inventory photo requested. Triggering camera thread...")
                # Lanzamos la cámara en un HILO APARTE para no bloquear la escucha del micrófono
                threading.Thread(target=self._procesar_escaneo, daemon=True).start()

    def _procesar_escaneo(self):
        # 1. Obtenemos coordenadas actuales del robot
        robot_x, robot_y = 0.0, 0.0
        odom = self.shared_data.get("odom", None)
        if odom:
            robot_x = odom.pose.pose.position.x
            robot_y = odom.pose.pose.position.y

        # 2. Capturamos la foto
        cap = cv2.VideoCapture(0)
        time.sleep(1) # Dejamos que la cámara enfoque 1 segundito
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print(f"{INDENT_OUTPUT}[{self.name}] Error: Could not access the camera hardware.")
            self._finalizar_escaneo()
            return

        # Convertimos a Base64
        _, buffer = cv2.imencode('.jpg', frame)
        b64_image = base64.b64encode(buffer).decode('utf-8')

        # 3. Enviamos a la Nube
        payload = {
            "imagen_base64": b64_image,
            "robot_x": robot_x,
            "robot_y": robot_y
        }

        print(f"{INDENT_OUTPUT}[{self.name}] Sending frame to Qwen Cloud API...")
        try:
            res = requests.post(self.cloud_scan_url, json=payload, timeout=20)
            res.raise_for_status()
            datos = res.json()
            
            if "imagen_anotada" in datos and datos["imagen_anotada"]:
                print(f"{INDENT_OUTPUT}[{self.name}] Scan successful. Items detected: {len(datos.get('detectado', []))}")
                self.publish_event(Event(
                    origin=self.name, 
                    type="UPDATE_DISPLAY_IMAGE", 
                    data={"image_b64": datos["imagen_anotada"], "title": "ESCANEANDO ESTANTERÍA..."}
                ))
        except Exception as e:
            print(f"{INDENT_OUTPUT}[{self.name}] Cloud communication error: {e}")

        # 4. Avisamos al navegador de que ya hemos acabado
        self._finalizar_escaneo()

    def _finalizar_escaneo(self):
        print(f"{INDENT_OUTPUT}[{self.name}] Visual workflow finished. Releasing motion locks.")
        self.publish_event(Event(origin=self.name, type="PHOTO_DONE"))
        self.is_scanning = False

    def run(self):
        self.data_stream['audio'] = None
        self.data_stream['distance'] = 5

        # calibramos un segundo completo para evitar falsos positivos de ruido
        print(f"{INDENT_OUTPUT}[{self.name}] Calibrating ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)


        threading.Thread(target=self._audio_loop, daemon=True).start()

        while self.running:
            try:
                task = self.task_queue.get(timeout=0.05)
                if hasattr(task, 'type'):
                    self.handle_task(task)
            except Empty:
                pass

        print(f"{INDENT_OUTPUT}[{self.name}] Stopped cleanly.")