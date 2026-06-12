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
        self.detected_text = "Esperando entrada por voz..."  # El que diu l'HUMÀ
        self.robot_text = ""                                  # El que diu el ROBOT
        self.panel_title = "PANEL DE CONTROL"
        self.dynamic_data = {}  
        self.footer_message = "Sistema Cart-ON actiu en local"
        
        # Comprovació automàtica d'entorn gràfic (per a Docker/Cloud)
        self.headless_mode = False
        if os.name == 'posix' and "DISPLAY" not in os.environ:
            self.headless_mode = True
            print(f"[{self.name}] Alerta: No es detecta monitor (Mode Cloud/Headless Actiu).")

        self.current_image = None # imatge si n'hi ha
        # Pintem la primera pantalla en repòs
        self.render_frame()

    def _clean_accents(self, text):
        """
        Neteja els accents i caràcters especials castellans/catalans 
        perquè les fonts d'OpenCV (ASCII) els puguin renderitzar correctament.
        """
        if not text:
            return ""
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U',
            '¿': '', '¡': '', 'à': 'a', 'è': 'e', 'ò': 'o',
            'À': 'A', 'È': 'E', 'Ò': 'O', 'ç': 'c', 'Ç': 'C'
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text

    def _draw_wrapped_text(self, img, text, x, y, max_width, font, font_scale, color, thickness, line_spacing=25):
        """
        Divideix un text llarg en diverses línies perquè s'ajusti a l'amplada màxima (max_width)
        i retorna la següent coordenada Y lliure.
        """
        text = self._clean_accents(text)
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            (line_w, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
            
            if line_w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines:
            cv2.putText(img, line, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
            y += line_spacing
        return y

    def update_data(self, status=None, text=None, robot_text=None, title=None, data_dict=None, footer=None, image=None):
        if status is not None: 
            self.current_status = status
            if status == "LISTENING":
                self.current_image = None
                self.robot_text = ""
                
        if text is not None: self.detected_text = text
        if robot_text is not None: self.robot_text = robot_text 
        if title is not None: self.panel_title = title.upper()
        if data_dict is not None: self.dynamic_data = data_dict
        if footer is not None: self.footer_message = footer
        
        if image is not None: 
            self.current_image = image
            
        self.render_frame()

    def render_frame(self):
        # 1. Fons de la interfície (Gris fosc/blau robòtic)
        self.frame[:] = (24, 19, 17)

        # 2. Dibuix de línies estructurals d'accent (Color segons l'estat)
        if self.current_status == "LISTENING":
            color_accent = (238, 182, 6) # Blau clàssic / Cian
        elif self.current_status == "PROCESSING":
            color_accent = (0, 140, 255)  # Taronja pensant
        elif self.current_status == "SUCCESS":
            color_accent = (50, 200, 50)  # Verd èxit
        elif self.current_status == "SHUTDOWN":
            color_accent = (50, 50, 200)  # Vermell
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

        # 4. Mostrar entrada de veu de l'usuari (STT) -> A DALT
        cv2.putText(self.frame, "TU HAS DICHO:", (40, 115), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)
        
        user_text = f'"{self.detected_text}"'
        self._draw_wrapped_text(self.frame, user_text, 40, 140, 720, 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, line_spacing=22)

        # 5. TARGETA CENTRAL DINÀMICA (Només per a imatge o la resposta de text de Cart-ON)
        cv2.rectangle(self.frame, (40, 190), (self.width - 40, self.height - 100), (35, 30, 27), -1)
        cv2.rectangle(self.frame, (40, 190), (self.width - 40, self.height - 100), (70, 70, 70), 1)

        # Títol del panell actual
        panel_title_clean = self._clean_accents(self.panel_title)
        cv2.putText(self.frame, panel_title_clean, (60, 220), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_accent, 1, cv2.LINE_AA)

        if self.current_image is not None:
            try:
                box_w = (self.width - 40) - 40   
                box_h = (self.height - 100) - 240 
                resized_img = cv2.resize(self.current_image, (box_w, box_h), interpolation=cv2.INTER_AREA)
                self.frame[240:240+box_h, 40:40+box_w] = resized_img
            except Exception as e:
                cv2.putText(self.frame, f"Error render imatge: {e}", (60, 265), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        else:
            # Mostrem el missatge del robot a la caixa central buida
            current_y = 255
            max_text_width = self.width - 120 
            
            if self.robot_text:
                cv2.putText(self.frame, "CART-ON DICE:", (60, current_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)
                current_y += 25
                
                # Text del robot net, blanc os i amb salt de línia automàtic
                robot_text_quotes = f'"{self.robot_text}"'
                color_gemini = (245, 235, 230) 
                self._draw_wrapped_text(self.frame, robot_text_quotes, 60, current_y, max_text_width,
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_gemini, 1, line_spacing=24)
            else:
                cv2.putText(self.frame, "Esperando respuesta de la nube...", (60, current_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)

        # 6. Peu de pàgina (Logs de baix nivell)
        footer_clean = self._clean_accents(self.footer_message)
        cv2.putText(self.frame, footer_clean, (40, self.height - 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1, cv2.LINE_AA)

    def refresh(self):
        if self.headless_mode:
            pass
        else:
            cv2.imshow("Cart-ON Monitor", self.frame)
            cv2.waitKey(1)

    def close(self):
        if not self.headless_mode:
            cv2.destroyAllWindows()