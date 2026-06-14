import os
import json
import base64
import cv2
import numpy as np
from openai import OpenAI
from ai_services.nlp_qwen import NLPQwen
from db.sql_manager import SQLManager

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
        print("[PlannerCloud] Orquestador Multimedia (Voz + Visión + Maps) iniciado.")
        self.sql = SQLManager()
        self.nlp = NLPQwen()
        self.estado_actual = "fase_2_interaccion"
        self.modo_entorno = "supermercado" 
        self.lista_compra = {}

    # =========================================================================
    # PIPELINE 1: VOZ, RECONOCIMIENTO DE INTENCIONES E INTERCEPTORES
    # =========================================================================
    def procesar_peticion_hri(self, texto_usuario: str, imagen_bytes: bytes, mime_type: str = "image/jpeg", lista_compra_local=None):
        if isinstance(lista_compra_local, dict):
            self.lista_compra = lista_compra_local.copy()
        
        texto_bajo = texto_usuario.lower()
        
        # =======================================================
        # CORTOCIRCUITO DE SEGURIDAD (SHUTDOWN HARDCODED)
        # =======================================================
        if "apágate" in texto_bajo or "apagar" in texto_bajo or "desconecta" in texto_bajo or "apagar sistemas" in texto_bajo:
            print("[PlannerCloud] Comando de apagado detectado por cortocircuito.")
            return crear_respuesta_cloud(
                texto="Entendido. Apagando todos los sistemas interactivos. Buenas noches.",
                estado_actual=self.estado_actual,
                emocion="feliz",
                lista_compra=self.lista_compra,
                intent="shutdown",
                accion_fisica="SHUTDOWN"
            )

        # 1. INTERCEPTORES DE CAMBIO DE MODO
        if "modo escuela" in texto_bajo:
            self.modo_entorno = "escuela"
            return crear_respuesta_cloud("Modo escuela activado. Ahora soy tu guía universitario de la UAB.", self.estado_actual, "feliz", self.lista_compra, "change_mode")
        elif "modo supermercado" in texto_bajo:
            self.modo_entorno = "supermercado"
            return crear_respuesta_cloud("Modo supermercado activado. Listo para rellenar la lista de la compra.", self.estado_actual, "feliz", self.lista_compra, "change_mode")

        # 2. PROCESAMIENTO SEMÁNTICO NORMAL CON QWEN NLP
        resultado_nlp = self.nlp.parse_intent(texto_usuario, modo=self.modo_entorno)
        
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

        # Variables multimedia del mapa (Universidad)
        aula_objetivo = None
        lat_objetivo = None
        lng_objetivo = None

       # --- CAPA DE NEGOCIO A: MODO SUPERMERCADO ---
        if self.modo_entorno == "supermercado":
            
            # 1. AÑADIR PRODUCTOS
            if intent == "add" and item != "producto desconocido":
                cantidad_final = quantity if quantity else 1
                self.lista_compra[item] = self.lista_compra.get(item, 0) + cantidad_final
                contexto_interno = f"Has añadido {cantidad_final} de {item} a la lista."
            
            # 2. ELIMINAR PRODUCTOS
            elif intent in ["remove", "delete", "clear", "drop"]:
                if item in ["todo", "lista", "la lista", "producto desconocido"] or "lista" in texto_bajo or "todo" in texto_bajo:
                    self.lista_compra.clear()
                    contexto_interno = "El usuario te ha pedido vaciar la lista. Hazlo saber diciendo que la lista está completamente limpia y lista para empezar de nuevo."
                elif item in self.lista_compra:
                    if not quantity or quantity >= self.lista_compra[item] or "todo" in texto_bajo or "todos" in texto_bajo:
                        del self.lista_compra[item]
                        contexto_interno = f"Has eliminado completamente el {item} de la lista de la compra. Ya no queda ninguno."
                    else:
                        self.lista_compra[item] -= quantity
                        contexto_interno = f"Has quitado {quantity} de {item} de la lista. Aún le quedan {self.lista_compra[item]} en la cesta."
                else:
                    contexto_interno = f"El usuario quiere borrar {item}, pero ese producto no está en su lista de la compra actual. Díselo con tacto."

            # 3. LEER LA LISTA
            elif intent == "read_list":
                if self.lista_compra:
                    elementos = [f"{cant} de {prod}" for prod, cant in self.lista_compra.items()]
                    lista_texto = ", ".join(elementos[:-1]) + (f" y {elementos[-1]}" if len(elementos) > 1 else elementos[0])
                    contexto_interno = f"Dile al usuario con entusiasmo los productos que tiene en su lista. Contiene exactamente: {lista_texto}."
                else:
                    contexto_interno = "Dile al usuario amablemente que su lista de la compra está vacía."

        # --- CAPA DE NEGOCIO B: MODO ESCUELA (UAB) ---
        elif self.modo_entorno == "escuela":
            if intent == "location_query":
                coords = self.sql.get_classroom_location(item)
                if coords:
                    aula_objetivo = item
                    lat_objetivo = coords['latitud']
                    lng_objetivo = coords['longitud']
                    contexto_interno = f"Le muestras en pantalla el mapa del aula {item}."
                        
            elif intent == "schedule_query":
                info_clases = self.sql.get_school_info(item, group, time_val)
                if info_clases and len(info_clases) == 1:
                    aula_objetivo = info_clases[0].get('aula')
                    lat_objetivo = info_clases[0].get('latitud')
                    lng_objetivo = info_clases[0].get('longitud')
                    contexto_interno = f"Has encontrado su clase en el aula {aula_objetivo}. Dile que le has puesto el mapa en pantalla."

        # 3. GENERAR RESPUESTA FINAL CON EMOCIÓN DE LOS OJOS
        if not contexto_interno:
            contexto_interno = "Responde amablemente a lo que te ha dicho el usuario."
            
        resultado_emocional = self.nlp.generate_response(texto_usuario, contexto_interno)
        respuesta_natural = resultado_emocional.get("texto")
        emocion_ojos = resultado_emocional.get("emocion", "neutral")
        
        if emocion_ojos == "neutral" and emocion_intent and emocion_intent != "neutro":
            emocion_ojos = emocion_intent

        print(f"[PlannerCloud] Emoción final inyectada: -> {emocion_ojos.upper()} <-")

        return crear_respuesta_cloud(
            texto=respuesta_natural, estado_actual=self.estado_actual, emocion=emocion_ojos,
            lista_compra=self.lista_compra, intent=intent, aula=aula_objetivo, lat=lat_objetivo,
            lng=lng_objetivo, accion_fisica=accion_final
        )

    # =========================================================================
    # PIPELINE 2: PROCESAMIENTO SILENCIOSO DE IMÁGENES DE INVENTARIO (VLM)
    # =========================================================================
    def procesar_escaneo_estanteria(self, imagen_base64: str):
        print(f"[Vision] Procesando imagen de inventario...")
        
        prompt = (
            "Eres el sistema de visión de un asistente de supermercado.\n"
            "Identifica los productos en la imagen y cuéntalos.\n"
            "REGLA ESTRICTA: Responde ÚNICA Y EXCLUSIVAMENTE con un JSON válido que sea una lista de objetos.\n"
            "Cada objeto debe tener 'producto', 'cantidad' y 'caja'.\n"
            "El campo 'caja' debe contener [y_min, x_min, y_max, x_max] en un rango de 0 a 1000.\n"
            "Ejemplo: [{\"producto\": \"Botella de agua\", \"cantidad\": 1, \"caja\": [200, 300, 400, 600]}]"
        )
        
        # 1. Inferencia del Modelo Visual de la UAB
        try:
            client = OpenAI(api_key="accesoAlLLM", base_url="https://dcc-llm.uab.cat/bes2/v1")
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
            print(f"[Vision] Detecciones del VLM: {detecciones}")
        except Exception as e:
            print(f"[Vision] Error en la inferencia del VLM: {e}")
            detecciones = []

        # 2. Guardar e indexar stock en MySQL (Sin coordenadas GPS locales)
        if detecciones:
            conn = self.sql.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    query = """
                        INSERT INTO productos (nombre_yolo, nombre_pantalla, precio, stock_actual)
                        VALUES (%s, %s, 0.00, %s)
                        ON DUPLICATE KEY UPDATE 
                            stock_actual = stock_actual + %s;
                    """
                    for item in detecciones:
                        nombre = item.get("producto", "")
                        cant = int(item.get("cantidad", 1))
                        if nombre:
                            n_limpio = nombre.strip().lower()
                            cursor.execute(query, (n_limpio, nombre.strip(), cant, cant))
                    conn.commit()
                    cursor.close()
                    print(f"[SQL] Actualización de stock completada.")
                except Exception as e:
                    print(f"[SQL] Error actualizando inventario: {e}")
                finally:
                    conn.close()

        # 3. Dibujar las Bounding Boxes sobre la imagen (OpenCV Headless RAM)
        img_anotada_b64 = None
        if detecciones:
            try:
                img_bytes = base64.b64decode(imagen_base64)
                img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
                alto, ancho = img.shape[:2]

                for item in detecciones:
                    caja = item.get("caja", [])
                    if len(caja) == 4:
                        # Qwen-VL usa formato [ymin, xmin, ymax, xmax] mapeado de 0 a 1000
                        y1, x1 = int(caja[0] * alto / 1000), int(caja[1] * ancho / 1000)
                        y2, x2 = int(caja[2] * alto / 1000), int(caja[3] * ancho / 1000)
                        
                        # Dibujamos rectángulo verde de bounding box
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        
                        # Colocamos la etiqueta con la cantidad encima
                        label = f"{item.get('producto', '???')} x{item.get('cantidad', 1)}"
                        cv2.putText(img, label, (x1, max(y1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                _, buffer = cv2.imencode('.jpg', img)
                img_anotada_b64 = base64.b64encode(buffer).decode('utf-8')
            except Exception as e:
                print(f"[Vision] Error al renderizar anotaciones OpenCV: {e}")

        return {"status": "ok", "detectado": detecciones, "imagen_anotada": img_anotada_b64}