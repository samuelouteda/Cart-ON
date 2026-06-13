from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
import cv2
import base64
import requests
import threading
import time

class VisionModule(BaseModule):
    """
    Módulo de Visión Local: Escucha peticiones de fotos, captura la cámara,
    consulta al Cloud y devuelve el resultado.
    """
    def __init__(self, name, event_bus, shared_data):
        super().__init__(name, event_bus)
        self.shared_data = shared_data
        
        # ⚠️ Cambia esto a la URL de tu Google Cloud Run real
        self.cloud_scan_url = "https://cart-on-api-225606614592.europe-west1.run.app/api/v1/escaneo_inventario"
        self.is_scanning = False

    def handle_task(self, task):
        # Escuchamos el grito del módulo de Navegación
        if task.type == "TAKE_INVENTORY_PHOTO":
            if not self.is_scanning:
                self.is_scanning = True
                print(f"{INDENT_OUTPUT}[{self.name}] 📸 ¡Orden de foto recibida! Arrancando cámara...")
                # Lanzamos en un hilo para no bloquear el bus de eventos del robot
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
        time.sleep(1) # Dejamos que la cámara enfoque
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print(f"{INDENT_OUTPUT}[{self.name}] 🔴 Error: No se pudo acceder a la cámara.")
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

        print(f"{INDENT_OUTPUT}[{self.name}] ☁️ Enviando foto a Qwen en la nube...")
        try:
            res = requests.post(self.cloud_scan_url, json=payload, timeout=20)
            res.raise_for_status()
            datos = res.json()
            
            # 4. Magia de vuelta: Pintamos en la interfaz local
            if "imagen_anotada" in datos and datos["imagen_anotada"]:
                # Le pedimos al orquestador que actualice el display con la foto procesada
                print(f"{INDENT_OUTPUT}[{self.name}] ✅ Escaneo OK. Productos detectados: {len(datos.get('detectado', []))}")
                
                # Simulamos una tarea visual (tu display cogerá esto si lo conectamos)
                self.publish_event(Event(
                    origin=self.name, 
                    type="UPDATE_DISPLAY_IMAGE", 
                    data={"image_b64": datos["imagen_anotada"], "title": "ESCANEANDO ESTANTERÍA..."}
                ))
                
        except Exception as e:
            print(f"{INDENT_OUTPUT}[{self.name}] 🔴 Error comunicando con el Cloud: {e}")

        # 5. Avisamos de que hemos acabado para que el robot siga conduciendo
        self._finalizar_escaneo()

    def _finalizar_escaneo(self):
        print(f"{INDENT_OUTPUT}[{self.name}] 🚀 Proceso de visión terminado. Liberando motores.")
        self.publish_event(Event(origin=self.name, type="PHOTO_DONE"))
        self.is_scanning = False

    def loop(self):
        # Módulo reactivo, no hace nada en su loop principal
        pass