import os
import json
import base64
import cv2
import numpy as np
from openai import OpenAI
from ai_services.nlp_qwen import NLPQwen
from db.sql_manager import SQLManager
from core.config import Config

def limpiar_nombre(texto):
    return texto.lower().strip() if texto else "producto desconocido"

def crear_respuesta_cloud(texto, estado_actual, emocion="neutral", lista_compra=None, intent=None, aula=None, lat=None, lng=None, accion_fisica="NINGUNA"):
    respuesta = {
        "status": "success",
        "texto": texto,
        "emocion": emocion,
        "estado_actual": estado_actual,
        "intent": intent,
        "aula": aula,
        "lat": lat,
        "lng": lng,
        "accion_fisica": accion_fisica
    }
    if lista_compra is not None:
        respuesta["lista_compra"] = dict(lista_compra)
    return respuesta

class PlannerCloud:
    def __init__(self):
        print("[PlannerCloud] Orquestador Dual Emocional iniciado.")
        self.sql = SQLManager()
        self.nlp = NLPQwen()
        self.estado_actual = "fase_2_interaccion"
        self.modo_entorno = "supermercado" 
        self.lista_compra = {}

    def procesar_peticion_hri(self, texto_usuario: str, imagen_bytes: bytes, mime_type: str = "image/jpeg", lista_compra_local=None):
        # SINCRONIZACIÓN DE ESTADO: Si el robot nos manda su lista, actualizamos la de la nube
        if isinstance(lista_compra_local, dict):
            self.lista_compra = lista_compra_local.copy()
        
        texto_bajo = texto_usuario.lower()
        
        if ("delta siete" in texto_bajo or "delta 7" in texto_bajo) and ("mapeo" in texto_bajo or "escanear" in texto_bajo):
            msg = f"Contraseña Delta Siete aceptada. Iniciando mapeo en modo {self.modo_entorno}."
            return crear_respuesta_cloud(msg, self.estado_actual, "feliz", self.lista_compra, "start_mapping", accion_fisica="INICIAR_MAPEO")
        
        palabras_movimiento = ["llévame", "llevame", "vamos", "guíame", "guiame", "conduce", "acompáñame"]
        quiere_moverse = any(p in texto_bajo for p in palabras_movimiento)
        
        if "modo escuela" in texto_bajo:
            self.modo_entorno = "escuela"
            return crear_respuesta_cloud("Modo escuela activado.", self.estado_actual, "feliz", self.lista_compra, "change_mode")
        elif "modo supermercado" in texto_bajo:
            self.modo_entorno = "supermercado"
            return crear_respuesta_cloud("Modo supermercado activado.", self.estado_actual, "feliz", self.lista_compra, "change_mode")

        resultado_nlp = self.nlp.parse_intent(texto_usuario, modo=self.modo_entorno)
        
        # BLOQUE BLINDADO ANTI-CRASHES (Ahora soporta los 7 elementos, incluyendo la emoción)
        if len(resultado_nlp) == 7:
            intent, item_crudo, quantity, group, time_val, reply, emocion_intent = resultado_nlp
        elif len(resultado_nlp) == 6:
            intent, item_crudo, quantity, group, time_val, reply = resultado_nlp
            emocion_intent = "neutral"
        else:
            intent, item_crudo, quantity, group, time_val, reply, emocion_intent = "unknown", "producto desconocido", 1, None, None, None, "neutral"

        item = limpiar_nombre(item_crudo)
        contexto_interno = ""
        accion_final = "NINGUNA"

        aula_objetivo = None
        lat_objetivo = None
        lng_objetivo = None

        if self.modo_entorno == "supermercado":
            if intent == "add" and item != "producto desconocido":
                cantidad_final = quantity if quantity else 1
                self.lista_compra[item] = self.lista_compra.get(item, 0) + cantidad_final
                contexto_interno = f"Añadido {cantidad_final} de {item} a la lista."
            elif intent == "read_list":
                contexto_interno = "Lee la lista de la compra."
            
            if quiere_moverse and self.lista_compra:
                accion_final = "INICIAR_CONDUCCION"
                contexto_interno = "Arrancando motores para buscar los productos de la lista."
            elif quiere_moverse and not self.lista_compra:
                contexto_interno = "Lista de compra vacía. Pide añadir productos primero."

        elif self.modo_entorno == "escuela":
            if intent == "location_query":
                coords = self.sql.get_classroom_location(item)
                if coords:
                    aula_objetivo = item
                    lat_objetivo = coords['latitud']
                    lng_objetivo = coords['longitud']
                    contexto_interno = f"Muestras mapa del aula {item}."
                    if quiere_moverse:
                        accion_final = "INICIAR_CONDUCCION"
                        contexto_interno = f"Guiando físicamente al aula {item}."
                        
            elif intent == "schedule_query":
                info_clases = self.sql.get_school_info(item, group, time_val)
                if info_clases and len(info_clases) == 1:
                    aula_objetivo = info_clases[0].get('aula')
                    lat_objetivo = info_clases[0].get('latitud')
                    lng_objetivo = info_clases[0].get('longitud')
                    if quiere_moverse and aula_objetivo:
                        accion_final = "INICIAR_CONDUCCION"
                        contexto_interno = f"Llevando a clase en aula {aula_objetivo}."

        if not contexto_interno:
            contexto_interno = "Responde amablemente a lo que te ha dicho el usuario."
            
        resultado_emocional = self.nlp.generate_response(texto_usuario, contexto_interno)
        respuesta_natural = resultado_emocional.get("texto")
        
        # LÓGICA DE PRIORIDAD EMOCIONAL
        emocion_ojos = resultado_emocional.get("emocion", "neutral")
        
        if emocion_ojos == "neutral" and emocion_intent and emocion_intent != "neutro":
            emocion_ojos = emocion_intent

        print(f"[PlannerCloud] Emoción final inyectada en la respuesta: -> {emocion_ojos.upper()} <-")

        # 3. Devolvemos el diccionario definitivo al HRI de la Raspberry usando la función auxiliar
        return crear_respuesta_cloud(
            texto=respuesta_natural, estado_actual=self.estado_actual, emocion=emocion_ojos,
            lista_compra=self.lista_compra, intent=intent, aula=aula_objetivo, lat=lat_objetivo,
            lng=lng_objetivo, accion_fisica=accion_final
        )

    def procesar_escaneo_estanteria(self, imagen_base64: str, robot_x: float, robot_y: float):
        prompt = (
            "Eres el sistema de visión de un robot de inventario de supermercado.\n"
            "Identifica los productos en la imagen y cuéntalos.\n"
            "REGLA ESTRICTA: Responde ÚNICA Y EXCLUSIVAMENTE con un JSON válido que sea una lista de objetos.\n"
            "Cada objeto debe tener 'producto', 'cantidad' y 'caja'.\n"
            "El campo 'caja' debe contener [y_min, x_min, y_max, x_max] en un rango de 0 a 1000.\n"
            "Ejemplo: [{\"producto\": \"Botella de agua\", \"cantidad\": 1, \"caja\": [200, 300, 400, 600]}]"
        )
        
        try:
            client = OpenAI(api_key=Config.UAB_TOKEN, base_url="https://dcc-llm.uab.cat/bes2/v1")
            response = client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagen_base64}"}}
                ]}],
                temperature=0.01
            )
            
            texto_crudo = response.choices[0].message.content.strip()
            if texto_crudo.startswith("```json"):
                texto_crudo = texto_crudo[7:-3].strip()
            elif texto_crudo.startswith("```"):
                texto_crudo = texto_crudo[3:-3].strip()
                
            detecciones = json.loads(texto_crudo)
        except Exception as e:
            print(f"Error LLM: {e}")
            detecciones = []

        if detecciones:
            conn = self.sql.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    query = """
                        INSERT INTO productos (nombre_yolo, nombre_pantalla, precio, stock_actual, pos_x, pos_y)
                        VALUES (%s, %s, 0.00, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            stock_actual = stock_actual + %s, pos_x = %s, pos_y = %s;
                    """
                    for item in detecciones:
                        nombre = item.get("producto", "")
                        cant = int(item.get("cantidad", 1))
                        if nombre:
                            n_limpio = nombre.strip().lower()
                            cursor.execute(query, (n_limpio, nombre.strip(), cant, robot_x, robot_y, cant, robot_x, robot_y))
                    conn.commit()
                    cursor.close()
                except Exception as e:
                    print(f"Error SQL: {e}")
                finally:
                    conn.close()

        img_anotada_b64 = None
        if detecciones:
            try:
                img_bytes = base64.b64decode(imagen_base64)
                img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                alto, ancho = img.shape[:2]

                for item in detecciones:
                    caja = item.get("caja", [])
                    if len(caja) == 4:
                        y1, x1 = int(caja[0] * alto / 1000), int(caja[1] * ancho / 1000)
                        y2, x2 = int(caja[2] * alto / 1000), int(caja[3] * ancho / 1000)
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        label = f"{item.get('producto', '???')} x{item.get('cantidad', 1)}"
                        cv2.putText(img, label, (x1, max(y1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                _, buffer = cv2.imencode('.jpg', img)
                img_anotada_b64 = base64.b64encode(buffer).decode('utf-8')
            except Exception as e:
                print(f"Error render: {e}")

        return {"status": "ok", "detectado": detecciones, "imagen_anotada": img_anotada_b64}