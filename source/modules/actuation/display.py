import cv2
import numpy as np
import os

class Display:
    def __init__(self, name, event_bus, shared_data):
        self.name = name
        self.event_bus = event_bus
        self.shared_data = shared_data
        
        # Dimensión de la pantalla digital en píxels (Monitor Principal)
        self.width = 800
        self.height = 600
        
        # Buffer en memoria
        self.frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Estados visuales iniciales
        self.current_status = "LISTENING"
        self.detected_text = "Esperando entrada por voz..." 
        self.robot_text = ""                                  
        self.panel_title = "PANEL DE CONTROL"
        self.dynamic_data = {}  
        self.footer_message = "Sistema Cart-ON (Modo Multimedia Local)"

        self.current_image = None 
        
        self.render_frame()

    def _clean_accents(self, text):
        if not text: return ""
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
        text = self._clean_accents(text)
        words = text.split(' ')
        lines, current_line = [], ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            (line_w, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
            if line_w <= max_width:
                current_line = test_line
            else:
                if current_line: lines.append(current_line)
                current_line = word
        if current_line: lines.append(current_line)

        for line in lines:
            cv2.putText(img, line, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
            y += line_spacing
        return y

    def update_data(self, status=None, text=None, robot_text=None, title=None, data_dict=None, footer=None, image=None):
        if status is not None: 
            if status == "LISTENING" and self.current_status != "LISTENING":
                self.current_image = None
                self.robot_text = ""
            self.current_status = status
                
        if text is not None: self.detected_text = text
        if robot_text is not None: self.robot_text = robot_text 
        if title is not None: self.panel_title = title.upper()
        if data_dict is not None: self.dynamic_data = data_dict
        if footer is not None: self.footer_message = footer
        if image is not None: self.current_image = image
        
        self.render_frame()

    def render_frame(self):
        # 1. Fons de la interfície
        self.frame[:] = (24, 19, 17)

        # 2. Colors d'estat
        color_accent = (0, 0, 255)
        if self.current_status == "LISTENING": color_accent = (238, 182, 6)
        elif self.current_status == "PROCESSING": color_accent = (0, 140, 255)
        elif self.current_status == "SUCCESS": color_accent = (50, 200, 50)
        elif self.current_status == "SPEAKING": color_accent = (255, 0, 255) 
        elif self.current_status == "SHUTDOWN": color_accent = (50, 50, 200)
            
        cv2.line(self.frame, (40, 80), (self.width - 40, 80), color_accent, 2)
        cv2.line(self.frame, (40, self.height - 70), (self.width - 40, self.height - 70), (80, 80, 80), 1)

        cv2.putText(self.frame, "CART-ON | SMART INTERFACE", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        status_str = f"[ STATUS: {self.current_status} ]"
        cv2.putText(self.frame, status_str, (self.width - 260, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_accent, 1, cv2.LINE_AA)

        cv2.putText(self.frame, "TU HAS DICHO:", (40, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)
        user_text = f'"{self.detected_text}"'
        self._draw_wrapped_text(self.frame, user_text, 40, 140, 720, cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, line_spacing=22)

        cv2.rectangle(self.frame, (40, 190), (self.width - 40, self.height - 100), (35, 30, 27), -1)
        cv2.rectangle(self.frame, (40, 190), (self.width - 40, self.height - 100), (70, 70, 70), 1)

        panel_title_clean = self._clean_accents(self.panel_title)
        cv2.putText(self.frame, panel_title_clean, (60, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_accent, 1, cv2.LINE_AA)

        if self.current_image is not None:
            try:
                box_w = (self.width - 40) - 40   
                box_h = (self.height - 100) - 240 
                resized_img = cv2.resize(self.current_image, (box_w, box_h), interpolation=cv2.INTER_AREA)
                self.frame[240:240+box_h, 40:40+box_w] = resized_img
            except Exception as e:
                cv2.putText(self.frame, f"Error render imatge: {e}", (60, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        else:
            current_y = 255
            max_text_width = self.width - 120 
            if self.robot_text:
                cv2.putText(self.frame, "CART-ON DICE:", (60, current_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)
                current_y += 25
                robot_text_quotes = f'"{self.robot_text}"'
                self._draw_wrapped_text(self.frame, robot_text_quotes, 60, current_y, max_text_width, cv2.FONT_HERSHEY_SIMPLEX, 0.55, (245, 235, 230), 1, line_spacing=24)
            else:
                cv2.putText(self.frame, "Esperando respuesta de la nube...", (60, current_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1, cv2.LINE_AA)

        footer_clean = self._clean_accents(self.footer_message)
        cv2.putText(self.frame, footer_clean, (40, self.height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1, cv2.LINE_AA)

    def refresh(self):
        cv2.imshow("Cart-ON Monitor", self.frame)
        cv2.waitKey(1)

    def close(self):
        cv2.destroyAllWindows()