from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

from queue import Empty
import time
import cv2
import base64
import requests
import threading

class SensoryModule(BaseModule):
    """
    Layer 3 (Multimedia): Módulo de Visión.
    Controla la cámara web local para sacar fotos bajo demanda y enviarlas al VLM.
    """
    def __init__(self, name, event_queue, shared_sensor_stream, data_task_bus, shared_data):
        super().__init__(name, event_queue)
        self.data_stream = shared_sensor_stream
        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        
        # Vision attributes
        self.cloud_url = "https://cart-on-api-sm-225606614592.europe-west1.run.app/api/v1/interaccion"
        self.is_scanning = False

    def loop(self):
        pass

    def handle_task(self, task):
        if task.type == "shutdown":
            self.running = False
            
        elif task.type == "TAKE_INVENTORY_PHOTO" or task.type == "TAKE_PHOTO":
            if not self.is_scanning:
                self.is_scanning = True
                print(f"{INDENT_OUTPUT}[{self.name}] Inventory photo requested. Triggering camera thread...")
                # Lanzamos la cámara en un HILO APARTE para no bloquear el sistema
                threading.Thread(target=self._procesar_escaneo, daemon=True).start()

    def _procesar_escaneo(self):
        # 1. Capturamos la foto con la Webcam del ordenador
        cap = cv2.VideoCapture(0)
        time.sleep(1) # Dejamos que la cámara enfoque 1 segundito
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print(f"{INDENT_OUTPUT}[{self.name}] Error: Could not access the webcam hardware.")
            self._finalizar_escaneo()
            return

        # Guardamos el último frame en la memoria compartida por si el HRI lo necesita
        # Lo convertimos a Base64 para el VLM
        _, buffer = cv2.imencode('.jpg', frame)
        b64_image = base64.b64encode(buffer).decode('utf-8')
        
        self.data_stream["last_frame"] = buffer.tobytes()

        # 2. Enviamos a la Nube (Sin datos de odometría/hardware)
        payload = {
            "imagen_base64": b64_image,
            "robot_x": 0.0, # Dummy data porque ya no hay robot físico
            "robot_y": 0.0
        }

        print(f"{INDENT_OUTPUT}[{self.name}] Sending frame to Qwen Cloud API...")
        try:
            res = requests.post(self.cloud_scan_url, json=payload, timeout=20)
            res.raise_for_status()
            datos = res.json()
            
            if "imagen_anotada" in datos and datos["imagen_anotada"]:
                print(f"{INDENT_OUTPUT}[{self.name}] Scan successful. Items detected: {len(datos.get('detectado', []))}")
                
                # Actualizamos la pantalla con la imagen que devuelve la IA (Bounding Boxes)
                self.publish_event(Event(
                    origin=self.name, 
                    type="UPDATE_DISPLAY_IMAGE", 
                    data={"image_b64": datos["imagen_anotada"], "title": "ESTANTERÍA ESCANEADA"}
                ))
        except Exception as e:
            print(f"{INDENT_OUTPUT}[{self.name}] Cloud communication error: {e}")

        # 3. Avisamos de que ya hemos acabado
        self._finalizar_escaneo()

    def _finalizar_escaneo(self):
        print(f"{INDENT_OUTPUT}[{self.name}] Visual workflow finished.")
        # Generamos el evento por si alguna otra parte de la lógica lo está esperando
        self.publish_event(Event(origin=self.name, type="PHOTO_DONE"))
        self.is_scanning = False

    def run(self):
        print(f"{INDENT_OUTPUT}[{self.name}] Started Vision Module.")

        while self.running:
            try:
                task = self.task_queue.get(timeout=0.05)
                if hasattr(task, 'type'):
                    self.handle_task(task)
            except Empty:
                pass

        print(f"{INDENT_OUTPUT}[{self.name}] Stopped cleanly.")