from core.base_module import BaseModule
from core.event import Event
from ultralytics import YOLO  # type: ignore
import cv2
import os

class Perception(BaseModule):
    def __init__(self, name, event_bus, shared_sensor_stream):
        super().__init__(name, event_bus)
        self.data_stream = shared_sensor_stream
        
        # 1. Cargar el modelo YOLO con tu archivo .pt
        ruta_modelo = os.path.join(os.path.dirname(__file__), "models", "yolo_best.pt")
        print(f"[{self.name}] Cargando cerebro YOLO desde: {ruta_modelo}")
        
        try:
            self.model = YOLO(ruta_modelo)
            print(f"[{self.name}] YOLO cargado correctamente.")
        except Exception as e:
            print(f"[{self.name}] ERROR al cargar YOLO: {e}")
            self.model = None

    def process_frame(self):
        if self.model is None:
            return

        # 2. Coger el frame de la cámara (asumiendo que SensorModule lo guarda aquí)
        frame = self.data_stream.get('frame')
        if frame is None:
            return

        # 3. Pasar el frame por YOLO (conf=0.6 significa que solo avisa si está 60%+ seguro)
        # verbose=False evita que llene la terminal de texto en cada frame
        resultados = self.model(frame, conf=0.6, verbose=False)
        
        # 4. Leer las detecciones
        for r in resultados:
            cajas = r.boxes
            for caja in cajas:
                # Obtener la clase detectada y la confianza
                id_clase = int(caja.cls[0])
                nombre_clase = self.model.names[id_clase]
                confianza = float(caja.conf[0])
                
                print(f"[{self.name}] 👀 Veo: {nombre_clase} (Confianza: {confianza:.2f})")

                # 5. Publicar el evento para que HRI o Planner reaccionen
                self.publish_event(
                    Event(
                        type="object_detected",
                        data={
                            "item": nombre_clase, 
                            "confidence": confianza
                        },
                        origin=self.name
                    )
                )

    def loop(self):
        self.process_frame()