import os
import json
import base64
import cv2
import numpy as np
import math
from openai import OpenAI
from ai_services.nlp_qwen import NLPQwen
from db.sql_manager import SQLManager
from core.config import Config

def limpiar_nombre(texto):
    return texto.lower().strip() if texto else "producto desconocido"

def crear_respuesta_cloud(texto, estado_actual, emocion="neutral", lista_compra=None, intent=None, aula=None, lat=None, lng=None, accion_fisica="NINGUNA", ruta_supermercado=None):
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
    if ruta_supermercado is not None:
        respuesta["ruta_supermercado"] = ruta_supermercado
    return respuesta

class PlannerCloud:
    def __init__(self):
        print("[PlannerCloud] Orquestador Universal Dual (FSM + Visión + Multipunto) iniciado.")
        self.sql = SQLManager()
        self.nlp = NLPQwen()
        self.estado_actual = "fase_2_interaccion"
        self.modo_entorno = "supermercado" 
        self.lista_compra = {}

    # =========================================================================
    # PIPELINE 1: VOZ, RECONOCIMIENTO DE INTENCIONES E INTERCEPTORES FSM
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
                texto="Entendido. Apagando todos los sistemas físicos y lógicos. Buenas noches.",
                estado_actual=self.estado_actual,
                emocion="feliz",
                lista_compra=self.lista_compra,
                intent="shutdown",
                accion_fisica="SHUTDOWN"
            )
        # =======================================================

        # 1. INTERCEPTOR ESTADO: MAPEO (Requiere contraseña de administrador)
        if ("modo admin" in texto_bajo or "modo administrador" in texto_bajo or "admin" in texto_bajo) and ("mapeo" in texto_bajo or "escanear" in texto_bajo):
            msg = f"Contraseña Delta Siete aceptada. Iniciando protocolo de escaneo y mapeo autónomo en modo {self.modo_entorno}."
            return crear_respuesta_cloud(msg, self.estado_actual, "feliz", self.lista_compra, "start_mapping", accion_fisica="INICIAR_MAPEO")
        
        # 2. DETECTOR DE INTENCIÓN DE MOVIMIENTO GENERAL
        palabras_movimiento = ["llévame", "llevame", "vamos", "guíame", "guiame", "conduce", "acompáñame"]
        quiere_moverse = any(p in texto_bajo for p in palabras_movimiento)
        
        # 3. INTERCEPTORES DE CAMBIO DE MODO
        if "modo escuela" in texto_bajo:
            self.modo_entorno = "escuela"
            return crear_respuesta_cloud("Modo escuela activado. Ahora soy tu guía universitario de la UAB.", self.estado_actual, "feliz", self.lista_compra, "change_mode")
        elif "modo supermercado" in texto_bajo:
            self.modo_entorno = "supermercado"
            return crear_respuesta_cloud("Modo supermercado activado. Listo para rellenar la lista de la compra.", self.estado_actual, "feliz", self.lista_compra, "change_mode")

        # 4. PROCESAMIENTO SEMÁNTICO NORMAL CON QWEN NLP
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
        
        # Variable de ruta multipunto (Supermercado)
        ruta_supermercado = None

       # --- CAPA DE NEGOCIO A: MODO SUPERMERCADO ---
        if self.modo_entorno == "supermercado":
            
            # 1. AÑADIR PRODUCTOS
            if intent == "add" and item != "producto desconocido":
                cantidad_final = quantity if quantity else 1
                self.lista_compra[item] = self.lista_compra.get(item, 0) + cantidad_final
                contexto_interno = f"Has añadido {cantidad_final} de {item} a la lista."
            
            # 2. ELIMINAR PRODUCTOS
            elif intent in ["remove", "delete", "clear", "drop"]:
                
                # CASO A: VACIAR LA LISTA ENTERA ("Borra la lista", "Quítalo todo")
                if item in ["todo", "lista", "la lista", "producto desconocido"] or "lista" in texto_bajo or "todo" in texto_bajo:
                    self.lista_compra.clear()
                    contexto_interno = "El usuario te ha pedido vaciar la lista. Hazlo saber diciendo que la lista está completamente limpia y lista para empezar de nuevo."
                
                # CASO B y C: ELIMINAR UN PRODUCTO ESPECÍFICO
                elif item in self.lista_compra:
                    # CASO B: Eliminar todos los paquetes de un producto ("Quita la leche", "Borra todos los cereales")
                    # Se activa si no especifica cantidad, si la cantidad es mayor al stock, o si dice "todo/todos"
                    if not quantity or quantity >= self.lista_compra[item] or "todo" in texto_bajo or "todos" in texto_bajo:
                        del self.lista_compra[item]
                        contexto_interno = f"Has eliminado completamente el {item} de la lista de la compra. Ya no queda ninguno."
                    
                    # CASO C: Eliminar solo una cantidad específica ("Quita 1 de leche")
                    else:
                        self.lista_compra[item] -= quantity
                        contexto_interno = f"Has quitado {quantity} de {item} de la lista. Aún le quedan {self.lista_compra[item]} en la cesta."
                
                # ERROR: Intenta borrar algo que no tiene
                else:
                    contexto_interno = f"El usuario quiere borrar {item}, pero ese producto no está en su lista de la compra actual. Díselo con tacto."

            # 3. LEER LA LISTA
            elif intent == "read_list":
                if self.lista_compra:
                    # Construimos un texto plano con los productos: "2 de leche, 1 de pan..."
                    elementos = [f"{cant} de {prod}" for prod, cant in self.lista_compra.items()]
                    lista_texto = ", ".join(elementos[:-1]) + (f" y {elementos[-1]}" if len(elementos) > 1 else elementos[0])
                    contexto_interno = f"Dile al usuario con entusiasmo los productos que tiene en su lista. Contiene exactamente: {lista_texto}."
                else:
                    contexto_interno = "Dile al usuario amablemente que su lista de la compra está vacía."
            
            # 4. LÓGICA DE RUTA MULTIPUNTO DEL SUPERMERCADO
            if quiere_moverse and self.lista_compra:
                accion_final = "INICIAR_CONDUCCION"
                contexto_interno = "Dile al usuario amablemente que vas a arrancar los motores para recorrer el supermercado y buscar los productos de su lista."
                
                ruta_supermercado = []
                conn = self.sql.get_connection()
                if conn:
                    try:
                        cursor = conn.cursor(dictionary=True)
                        for prod in self.lista_compra.keys():
                            prod_limpio = prod.lower().strip()
                            cursor.execute("SELECT pos_x, pos_y FROM productos WHERE nombre_yolo = %s OR nombre_pantalla = %s", (prod_limpio, prod_limpio))
                            res = cursor.fetchone()
                            if res and res['pos_x'] is not None:
                                ruta_supermercado.append({
                                    "producto": prod, 
                                    "x": res['pos_x'], 
                                    "y": res['pos_y']
                                })
                        cursor.close()
                    except Exception as e:
                        print(f"Error extrayendo coordenadas de productos: {e}")
                    finally:
                        conn.close()
                        
            elif quiere_moverse and not self.lista_compra:
                contexto_interno = "El usuario quiere que le lleves por el súper, pero la lista está vacía. Dile que añada algún producto primero antes de arrancar."

        # --- CAPA DE NEGOCIO B: MODO ESCUELA (UAB) ---
        elif self.modo_entorno == "escuela":
            if intent == "location_query":
                coords = self.sql.get_classroom_location(item)
                if coords:
                    aula_objetivo = item
                    lat_objetivo = coords['latitud']
                    lng_objetivo = coords['longitud']
                    contexto_interno = f"Le muestras en pantalla el mapa del aula {item}."
                    
                    if quiere_moverse:
                        accion_final = "INICIAR_CONDUCCION"
                        contexto_interno = f"Dile de forma animada que le vas a guiar físicamente hasta el aula {item}. Que te siga."
                        
            elif intent == "schedule_query":
                info_clases = self.sql.get_school_info(item, group, time_val)
                if info_clases and len(info_clases) == 1:
                    aula_objetivo = info_clases[0].get('aula')
                    lat_objetivo = info_clases[0].get('latitud')
                    lng_objetivo = info_clases[0].get('longitud')
                    
                    if quiere_moverse and aula_objetivo:
                        accion_final = "INICIAR_CONDUCCION"
                        contexto_interno = f"Has encontrado su clase en el aula {aula_objetivo}. Dile que le vas a llevar físicamente hasta allí ahora mismo."

        # 5. GENERAR RESPUESTA FINAL CON EMOCIÓN DE LOS OJOS
        if not contexto_interno:
            contexto_interno = "Responde amablemente a lo que te ha dicho el usuario."
            
        resultado_emocional = self.nlp.generate_response(texto_usuario, contexto_interno)
        respuesta_natural = resultado_emocional.get("texto")
        emocion_ojos = resultado_emocional.get("emocion", "neutral")
        
        if emocion_ojos == "neutral" and emocion_intent and emocion_intent != "neutro":
            emocion_ojos = emocion_intent

        print(f"[PlannerCloud] Emoción final inyectada: -> {emocion_ojos.upper()} <- | Acción: {accion_final}")

        return crear_respuesta_cloud(
            texto=respuesta_natural, estado_actual=self.estado_actual, emocion=emocion_ojos,
            lista_compra=self.lista_compra, intent=intent, aula=aula_objetivo, lat=lat_objetivo,
            lng=lng_objetivo, accion_fisica=accion_final, ruta_supermercado=ruta_supermercado
        )

    # =========================================================================
    # PIPELINE 2: PROCESAMIENTO SILENCIOSO DE IMÁGENES DE INVENTARIO (VLM)
    # =========================================================================
    def procesar_escaneo_estanteria(self, imagen_base64: str, robot_x: float, robot_y: float):
        print(f"[Vision] Procesando escaneo de estantería. Posición Robot: X={robot_x:.2f}, Y={robot_y:.2f}")
        
        prompt = (
            "Eres el sistema de visión de un robot de inventario de supermercado.\n"
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

        # 2. Guardar e indexar espacialmente en MySQL
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
                    print(f"[SQL] Indexación espacial completada con éxito.")
                except Exception as e:
                    print(f"[SQL] Error insertando inventario: {e}")
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