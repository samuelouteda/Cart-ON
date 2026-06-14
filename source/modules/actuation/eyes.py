import threading
import time
import cv2
import numpy as np

class RobotEyes:
    def __init__(self, name):
        self.name = name
        self.emocion_actual = "neutral"
        self.running = True
        self.lock = threading.Lock()
        
        print(f"[{self.name}] Simulador de pantallas OLED inicializado en OpenCV.")
        threading.Thread(target=self._bucle_refresco, daemon=True).start()

    def set_emocion(self, nueva_emocion):
        """Actualiza la emoción que deben mostrar los ojos."""
        with self.lock:
            self.emocion_actual = nueva_emocion.lower()
            print(f"[{self.name}] Cambiando expresión a: {self.emocion_actual}")

    def _bucle_refresco(self):
        """Hilo en segundo plano que dibuja los ojos con OpenCV simulando las pantallas OLED."""
        while self.running:
            with self.lock:
                emocion = self.emocion_actual
                
            # Lienzo negro simulando la pantalla OLED de 128x64 ampliada para verla bien
            img = np.zeros((150, 250, 3), dtype=np.uint8)
            
            # Centro del ojo
            center_x, center_y = 125, 75

            if emocion == "feliz":
                # Arco hacia arriba simulando ojo feliz cerrado
                cv2.ellipse(img, (center_x, center_y+20), (60, 40), 0, 180, 360, (255, 255, 255), 10)
                
            elif emocion == "triste":
                # Óvalo blanco (ojo)
                cv2.ellipse(img, (center_x, center_y), (50, 60), 0, 0, 360, (255, 255, 255), -1)
                # Párpado caído cortando por arriba
                cv2.rectangle(img, (0, 0), (250, center_y-10), (0, 0, 0), -1)
                # Pupila mirando abajo
                cv2.circle(img, (center_x, center_y+30), 15, (0, 0, 0), -1)
                
            elif emocion == "duda":
                # Óvalo blanco
                cv2.ellipse(img, (center_x, center_y), (50, 60), 0, 0, 360, (255, 255, 255), -1)
                # Pupila desviada a la derecha
                cv2.circle(img, (center_x+25, center_y), 15, (0, 0, 0), -1)
                
            else:
                # Neutral: Mirando al frente
                cv2.ellipse(img, (center_x, center_y), (50, 60), 0, 0, 360, (255, 255, 255), -1)
                cv2.circle(img, (center_x, center_y), 15, (0, 0, 0), -1)

            cv2.imshow("Ojos OLED (Simulador)", img)
            cv2.waitKey(100) # Refresco a 10 FPS

    def stop(self):
        self.running = False
        cv2.destroyAllWindows()