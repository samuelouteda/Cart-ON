import threading
import time
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import sh1106

class RobotEyes:
    def __init__(self):
        self.device = self._inicialitzar_ulls()
        self.emocion_actual = "neutral"
        self.running = True
        self.lock = threading.Lock()
        
        # Arrancamos un hilo independiente solo para mantener las pantallas vivas
        if self.device:
            threading.Thread(target=self._bucle_refresco, daemon=True).start()

    def _inicialitzar_ulls(self):
        try:
            serial = spi(port=0, device=0, gpio_DC=20, gpio_RST=16, bcm_CS=21)
            dispositiu = sh1106(serial, width=128, height=64)
            print("[Eyes] 👀 Pantalles OLED SH1106 inicialitzades per SPI!")
            return dispositiu
        except Exception as e:
            print(f"[Eyes] ❌ Error de configuració de pins SPI: {e}")
            return None

    def set_emocion(self, nueva_emocion):
        """Actualiza la emoción que deben mostrar los ojos."""
        with self.lock:
            self.emocion_actual = nueva_emocion.lower()
            print(f"[Eyes] 🎭 Cambiando expresión a: {self.emocion_actual}")

    def _bucle_refresco(self):
        """Hilo en segundo plano que dibuja el ojo según la emoción actual."""
        while self.running:
            with self.lock:
                emocion = self.emocion_actual
                
            if self.device:
                with canvas(self.device) as draw:
                    # Fondo negro
                    draw.rectangle(self.device.bounding_box, outline="black", fill="black")
                    
                    if emocion == "feliz":
                        # Ojo feliz (forma de arco o U invertida)
                        draw.arc((24, 20, 104, 60), start=180, end=0, fill="white", width=8)
                        
                    elif emocion == "triste":
                        # Ojo triste (párpado superior caído)
                        draw.ellipse((24, 15, 104, 62), fill="white")
                        draw.rectangle((24, 0, 104, 30), fill="black") # Corta la mitad superior
                        draw.ellipse((52, 35, 76, 59), fill="black") # Pupila mirando abajo
                        
                    elif emocion == "duda":
                        # Ojo mirando hacia un lado
                        draw.ellipse((24, 2, 104, 62), fill="white")
                        draw.ellipse((70, 22, 94, 46), fill="black") # Pupila a la derecha
                        
                    else:
                        # Neutral (mirada al frente)
                        draw.ellipse((24, 2, 104, 62), fill="white")
                        draw.ellipse((52, 22, 76, 46), fill="black")

            # Refresca a 10 FPS (suficiente para OLEDs estáticas)
            time.sleep(0.1)

    def stop(self):
        """Apaga las pantallas al cerrar el programa."""
        self.running = False
        if self.device:
            self.device.clear()