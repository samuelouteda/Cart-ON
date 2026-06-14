import cv2
import numpy as np
import os
import serial
import json
import threading
import time

class Display:
    def __init__(self, name, event_bus, shared_data):
        self.name = name
        self.event_bus = event_bus
        self.shared_data = shared_data
        
        # Dimensió de la pantalla digital en píxels (Monitor Principal)
        self.width = 800
        self.height = 600
        
        # Buffer en memòria
        self.frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Estats visuals inicials
        self.current_status = "LISTENING"
        self.detected_text = "Esperando entrada por voz..." 
        self.robot_text = ""                                  
        self.panel_title = "PANEL DE CONTROL"
        self.dynamic_data = {}  
        self.footer_message = "Sistema Cart-ON actiu en local"
        
        # Mode Headless (Sense monitor)
        self.headless_mode = False
        if os.name == 'posix' and "DISPLAY" not in os.environ:
            self.headless_mode = True
            print(f"[{self.name}] Alerta: No es detecta monitor (Mode Cloud/Headless Actiu).")

        self.current_image = None 
        
        # =========================================================
        # 🔌 CONEXIÓN USB CON LA LILYGO (ESP32 E-Ink)
        # =========================================================
        self.lilygo_serial = None
        self.puerto_usb = 'ttyUcSB1'  # Cámbialo a /dev/ttyACM0 o /dev/ttyUcSB0 en la Raspberry
        self.baud_rate = 2000000  # 🚀 Subido a 2M para aguantar imágenes
        self.serial_lock = threading.Lock() # Bloqueo para evitar colisiones de hilos
        
        try:
            self.lilygo_serial = serial.Serial(self.puerto_usb, self.baud_rate, timeout=8)
            # Evita resetear la placa al conectar
            self.lilygo_serial.setDTR(False)
            self.lilygo_serial.setRTS(False)
            time.sleep(1)
            print(f"[{self.name}] ✅ Pantalla LilyGo conectada en {self.puerto_usb}")
        except Exception as e:
            print(f"[{self.name}] ⚠️ No se detectó LilyGo en {self.puerto_usb}. Solo OpenCV.")
        # =========================================================

        self.render_frame()
        self._enviar_texto_lilygo() # Enviamos el estado inicial en texto

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

    # =========================================================
    # 🎨 FUNCIONES DE CONVERSIÓN PARA LILYGO E-INK
    # =========================================================
    def _componer_lienzo_lilygo(self, titulo, imagen_mapa):
        """Lienzo minimalista para la LilyGo: Título grande y Mapa Gigante."""
        lienzo = np.ones((540, 960, 3), dtype=np.uint8) * 255
        cv2.putText(lienzo, self._clean_accents(titulo), (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 4)
        
        if imagen_mapa is not None:
            alto_mapa, ancho_mapa = imagen_mapa.shape[:2]
            max_w, max_h = 900, 440
            
            escala = min(max_w / ancho_mapa, max_h / alto_mapa)
            nuevo_ancho = int(ancho_mapa * escala)
            nuevo_alto = int(alto_mapa * escala)
            
            mapa_redimensionado = cv2.resize(imagen_mapa, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)
            
            x_offset = (960 - nuevo_ancho) // 2
            y_offset = 80 + (440 - nuevo_alto) // 2 
            lienzo[y_offset:y_offset+nuevo_alto, x_offset:x_offset+nuevo_ancho] = mapa_redimensionado
            
        return lienzo

    def _empaquetar_imagen_lilygo(self, img_cv2):
        """Convierte el lienzo OpenCV a escala de grises de 4-bits."""
        img_gray = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2GRAY)
        img_16_tonos = (img_gray // 16).astype(np.uint8)
        
        pixeles_izquierdos = img_16_tonos[:, 0::2]
        pixeles_derechos = img_16_tonos[:, 1::2]
        imagen_empaquetada = (pixeles_izquierdos << 4) | pixeles_derechos
        return imagen_empaquetada.tobytes()

    # =========================================================
    # 🚀 PROTOCOLOS DE ENVÍO POR USB (THREAD-SAFE)
    # =========================================================
    def _enviar_texto_lilygo(self):
        """Envía el estado clásico en JSON cuando no hay mapa."""
        if not self.lilygo_serial or not self.lilygo_serial.is_open: return
        
        paquete = {
            "status": self.current_status,
            "user": self._clean_accents(self.detected_text),
            "robot": self._clean_accents(self.robot_text)
        }
        datos_str = json.dumps(paquete) + "\n"
        
        if not hasattr(self, 'ultimo_json_enviado') or self.ultimo_json_enviado != datos_str:
            def enviar_task():
                with self.serial_lock:
                    try:
                        self.lilygo_serial.write(datos_str.encode('utf-8'))
                        self.lilygo_serial.flush()
                        self.ultimo_json_enviado = datos_str
                    except Exception as e:
                        print(f"[{self.name}] ⚠️ Error enviando texto LilyGo: {e}")
            threading.Thread(target=enviar_task, daemon=True).start()

    def _enviar_imagen_lilygo_hilo(self, titulo, imagen_mapa):
        """Hilo para enviar el mapa por el protocolo Ping-Pong sin congelar el robot."""
        if not self.lilygo_serial or not self.lilygo_serial.is_open: return
        
        print(f"[{self.name}] 🎨 Preparando imagen gigante para E-Ink...")
        lienzo_final = self._componer_lienzo_lilygo(titulo, imagen_mapa)
        datos_binarios = self._empaquetar_imagen_lilygo(lienzo_final)
        
        with self.serial_lock:
            try:
                self.lilygo_serial.reset_input_buffer()
                print(f"[{self.name}] 📡 Sincronizando con LilyGO para enviar imagen...")
                self.lilygo_serial.write((json.dumps({"type": "image"}) + "\n").encode('utf-8'))
                
                respuesta = self.lilygo_serial.readline().decode('utf-8').strip()
                if "READY" in respuesta:
                    tamano_bloque = 4096
                    for i in range(0, len(datos_binarios), tamano_bloque):
                        bloque = datos_binarios[i : i + tamano_bloque]
                        self.lilygo_serial.write(bloque)
                        if self.lilygo_serial.readline().decode('utf-8').strip() != "NEXT":
                            break
                    print(f"[{self.name}] 🤖 [LILYGO]: {self.lilygo_serial.readline().decode('utf-8').strip()}")
                else:
                    print(f"[{self.name}] 🔴 LilyGO no respondió READY: {respuesta}")
            except Exception as e:
                print(f"[{self.name}] 🔴 Error enviando imagen a LilyGO: {e}")

    # =========================================================
    # 🖥️ FUNCIONES DE RENDERIZADO OPENCV
    # =========================================================
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
        cambio_de_estado_radical = False
        
        if status is not None: 
            if status == "LISTENING" and self.current_status != "LISTENING":
                self.current_image = None
                self.robot_text = ""
                cambio_de_estado_radical = True
            self.current_status = status
                
        if text is not None: self.detected_text = text
        if robot_text is not None: self.robot_text = robot_text 
        if title is not None: self.panel_title = title.upper()
        if data_dict is not None: self.dynamic_data = data_dict
        if footer is not None: self.footer_message = footer
        
        self.render_frame()
        
        # 🚀 DECISOR DE ENVÍO A LILYGO
        if image is not None: 
            self.current_image = image
            # Disparamos el hilo del protocolo Ping-Pong de imagen
            threading.Thread(target=self._enviar_imagen_lilygo_hilo, args=(self.panel_title, image), daemon=True).start()
        else:
            # Si vuelve a escuchar, mandamos el JSON de texto normal
            self._enviar_texto_lilygo()

    def render_frame(self):
        # 1. Fons de la interfície
        self.frame[:] = (24, 19, 17)

        # 2. Colors d'estat
        color_accent = (0, 0, 255)
        if self.current_status == "LISTENING": color_accent = (238, 182, 6)
        elif self.current_status == "PROCESSING": color_accent = (0, 140, 255)
        elif self.current_status == "SUCCESS": color_accent = (50, 200, 50)
        elif self.current_status == "SPEAKING": color_accent = (255, 0, 255) # Magenta para hablar
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
        if not self.headless_mode:
            cv2.imshow("Cart-ON Monitor", self.frame)
            cv2.waitKey(1)

    def close(self):
        if self.lilygo_serial and self.lilygo_serial.is_open:
            self.lilygo_serial.close()
        if not self.headless_mode:
            cv2.destroyAllWindows()