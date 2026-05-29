import cv2
import numpy as np
import os

class Display:
    def __init__(self, name, event_bus, shared_data):
        self.name = name
        self.event_bus = event_bus
        self.shared_data = shared_data
        
        # Dimensió de la pantalla digital en píxels
        self.width = 800
        self.height = 600
        
        # Buffer en memòria (imatge en blanc/negre inicialment)
        self.frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Estats visuals inicials de l'assistent genèric
        self.current_status = "LISTENING"
        self.detected_text = "Esperando entrada por voz..."
        self.panel_title = "PANEL DE CONTROL"
        self.dynamic_data = {}  # Aquí guardarem qualsevol diccionari Key-Value (horaris, productes, rutes)
        self.footer_message = "Sistema Cart-ON actiu en local"
        
        # Comprovació automàtica d'entorn gràfic (per a Docker/Cloud)
        # Si correm a Linux/Docker sense X11, 'DISPLAY' no estarà definit
        self.headless_mode = False
        if os.name == 'posix' and "DISPLAY" not in os.environ:
            self.headless_mode = True
            print(f"[{self.name}] Alerta: No es detecta monitor (Mode Cloud/Headless Actiu).")

        # Pintem la primera pantalla en repòs
        self.render_frame()

    def update_data(self, status=None, text=None, title=None, data_dict=None, footer=None):
        """
        Mètode universal per injectar dades des de l'HRI. 
        Suporta qualsevol estructura de dades gràcies a data_dict.
        """
        if status is not None: self.current_status = status
        if text is not None: self.detected_text = text
        if title is not None: self.panel_title = title.upper()
        if data_dict is not None: self.dynamic_data = data_dict
        if footer is not None: self.footer_message = footer

        # Cada vegada que entren dades noves, redibuixem la matriu de píxels
        self.render_frame()

    def render_frame(self):
        """
        Genera el dibuix digital des de zero en la memòria RAM (matriu NumPy)
        """
        # 1. Fons de la interfície (Gris fosc/blau robòtic)
        self.frame[:] = (24, 19, 17)

        # 2. Dibuix de línies estructurals d'accent (Color Cian/Groguenc segons l'estat)
        color_accent = (238, 182, 6) if self.current_status == "LISTENING" else (50, 200, 50)
        if self.current_status == "LISTENING":
            color_accent = (238, 182, 6) # Cian/Blau clàssic
        elif self.current_status == "CONFUSED":
            color_accent = (0, 140, 255)  # Taronja suau/amable (BGR)
        elif self.current_status == "SUCCESS":
            color_accent = (50, 200, 50)  # Verd èxit
        elif self.current_status == "SHUTDOWN":
            color_accent = (50, 50, 200)  # Vermell granat o color de tancament (BGR)
        else:
            color_accent = (0, 0, 255)
        cv2.line(self.frame, (40, 80), (self.width - 40, 80), color_accent, 2)
        cv2.line(self.frame, (40, self.height - 70), (self.width - 40, self.height - 70), (80, 80, 80), 1)

        # 3. Textos fixos de la capçalera
        cv2.putText(self.frame, "CART-ON | SMART INTERFACE", (40, 55), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        
        status_str = f"[ STATUS: {self.current_status} ]"
        cv2.putText(self.frame, status_str, (self.width - 260, 52), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_accent, 1, cv2.LINE_AA)

        # 4. Mostrar entrada de veu de l'usuari (STT)
        cv2.putText(self.frame, "VEU DETECTADA (STT):", (40, 120), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)
        
        # Envolcall de text simple per si la frase és llarga
        user_text = f'"{self.detected_text}"'
        cv2.putText(self.frame, user_text, (40, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1, cv2.LINE_AA)

        # 5. TARGETA CENTRAL DINÀMICA (Agnòstica al tipus de dades)
        # Dibuixem el contenidor de fons del panell central
        cv2.rectangle(self.frame, (40, 190), (self.width - 40, self.height - 100), (35, 30, 27), -1)
        cv2.rectangle(self.frame, (40, 190), (self.width - 40, self.height - 100), (70, 70, 70), 1)

        # Títol del panell actual (Llista de la compra, Horaris, Localització, etc.)
        cv2.putText(self.frame, self.panel_title, (60, 225), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_accent, 1, cv2.LINE_AA)

        # RENDERITZACIÓ KEY-VALUE AUTOMÀTICA
        # Comencem a pintar a la línia Y = 265, i anem baixant per cada clau
        current_y = 265
        if not self.dynamic_data:
            cv2.putText(self.frame, "No hi ha dades disponibles en aquest panell.", (60, current_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)
        else:
            for key, value in self.dynamic_data.items():
                # Si ens passem del límit de la targeta, deixem de pintar per evitar desbordaments
                if current_y > self.height - 130:
                    cv2.putText(self.frame, "[... Més dades ocultes per espai ...]", (60, current_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
                    break
                
                # Format de la línia: "Clau: Valor"
                line_text = f"-> {key}: {value}"
                cv2.putText(self.frame, line_text, (60, current_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1, cv2.LINE_AA)
                current_y += 30 # Espaiat vertical entre línies

        # 6. Peu de pàgina (Logs de baix nivell / Debug)
        cv2.putText(self.frame, self.footer_message, (40, self.height - 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1, cv2.LINE_AA)

    def refresh(self):
        """
        Aquest mètode l'executarà el loop d'HRI contínuament.
        S'encarrega d'enviar el buffer a la pantalla física o de gestionar el mode Docker.
        """
        if self.headless_mode:
            # Al núvol / Docker: No fem cv2.imshow (petaria).
            # Com a alternativa de debug, podem guardar la imatge en disc cada X temps si volem
            # cv2.imwrite("display_debug.png", self.frame)
            pass
        else:
            # En local: Mostrem la finestra gràfica amb OpenCV de forma normal
            cv2.imshow("Cart-ON Monitor", self.frame)
            # waitKey(1) processa els esdeveniments gràfics interns del sistema operatiu
            cv2.waitKey(1)

    def close(self):
        """Tanca de forma neta les finestres al destruir el mòdul"""
        if not self.headless_mode:
            cv2.destroyAllWindows()