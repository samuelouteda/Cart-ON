import os
from ai_services.nlp_qwen import NLPQwen
from db.sql_manager import SQLManager

# Función auxiliar para limpiar el nombre
def limpiar_nombre(texto):
    if not texto:
        return "producto desconocido"
    return texto.lower().strip()

# Función auxiliar mejorada para incluir la emoción y datos multimedia
def crear_respuesta_cloud(texto, estado_actual, emocion="neutral", lista_compra=None, intent=None, aula=None, lat=None, lng=None):
    respuesta = {
        "status": "success",
        "texto": texto,
        "emocion": emocion,
        "estado_actual": estado_actual,
        "intent": intent,
        "aula": aula,
        "lat": lat,
        "lng": lng
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
        
        # Variables de estado
        self.modo_entorno = "supermercado" 
        self.lista_compra = {}
        self.memoria_escuela = {"tema_pendiente": None}

    def procesar_peticion_hri(self, texto_usuario: str, imagen_bytes: bytes, mime_type: str = "image/jpeg", lista_compra_local=None):
        # SINCRONIZACIÓN DE ESTADO: Si el robot nos manda su lista, actualizamos la de la nube
        if isinstance(lista_compra_local, dict):
            self.lista_compra = lista_compra_local.copy()
        
        texto_bajo = texto_usuario.lower()
        
        # INTERCEPTORES DE CAMBIO DE MODO CON EMOCIONES ASIGNADAS
        if "modo escuela" in texto_bajo:
            self.modo_entorno = "escuela"
            return crear_respuesta_cloud("Modo escuela activado. Ahora soy tu guia universitario de la UAB.", self.estado_actual, "feliz", self.lista_compra, "change_mode")
        elif "modo supermercado" in texto_bajo:
            self.modo_entorno = "supermercado"
            return crear_respuesta_cloud("Modo supermercado activado. Listo para hacer la compra.", self.estado_actual, "feliz", self.lista_compra, "change_mode")
        elif "modo" in texto_bajo and "cambia" in texto_bajo:
            return crear_respuesta_cloud("Solo dispongo de dos modos: Modo Escuela y Modo Supermercado. Por favor, dime cual prefieres.", self.estado_actual, "duda", self.lista_compra, "change_mode")

        # 1. Analizamos la intención semántica de la frase
        resultado_nlp = self.nlp.parse_intent(texto_usuario, modo=self.modo_entorno)
        
        # BLOQUE BLINDADO ANTI-CRASHES (Ahora soporta los 7 elementos, incluyendo la emoción)
        if len(resultado_nlp) == 7:
            intent, item_crudo, quantity, group, time_val, reply, emocion_intent = resultado_nlp
        elif len(resultado_nlp) == 6:
            intent, item_crudo, quantity, group, time_val, reply = resultado_nlp
            emocion_intent = "neutral"
        elif len(resultado_nlp) == 5:
            intent, item_crudo, group, time_val, reply = resultado_nlp
            quantity = 1
            emocion_intent = "neutral"
        else:
            intent, item_crudo, quantity, group, time_val, reply, emocion_intent = "unknown", "producto desconocido", 1, None, None, None, "neutral"

        item = limpiar_nombre(item_crudo)
        contexto_interno = ""

        # Variables multimedia del mapa
        aula_objetivo = None
        lat_objetivo = None
        lng_objetivo = None

        # --- CAPA SENSORIAL A: SUPERMERCADO ---
        if self.modo_entorno == "supermercado":
            if intent == "chat":
                contexto_interno = "Estas en el supermercado. El usuario charla. Responde de forma amistosa."
            elif intent == "add":
                if item != "producto desconocido":
                    cantidad_final = quantity if quantity else 1
                    self.lista_compra[item] = self.lista_compra.get(item, 0) + cantidad_final
                    contexto_interno = f"Confirma amablemente que has anadido {cantidad_final} de {item} a la lista de la compra."
                else:
                    contexto_interno = "El usuario quiere anadir algo pero no has entendido que es. Pidele que lo repita."
            elif intent == "delete":
                if item in self.lista_compra:
                    del self.lista_compra[item]
                    contexto_interno = f"Confirma que has quitado {item} de la lista de la compra."
                else:
                    contexto_interno = f"Dile al usuario que {item} no estaba en su lista de la compra."
            elif intent == "read_list":
                if self.lista_compra:
                    productos = ", ".join([f"{cant} de {prod}" for prod, cant in self.lista_compra.items()])
                    contexto_interno = f"Dile al usuario que en su lista tiene: {productos}."
                else:
                    contexto_interno = "Dile al usuario que su lista de la compra esta vacia actualmente."
            elif intent == "clear":
                self.lista_compra.clear()
                contexto_interno = "Confirma que has vaciado completamente la lista de la compra."
            elif intent in ["read_stock", "check_availability"]:
                if item != "producto desconocido":
                    producto_info = self.sql.get_product_info(item)
                    if producto_info:
                        nombre = producto_info.get("nombre_pantalla", item)
                        precio = producto_info.get("precio", "desconocido")
                        stock = producto_info.get("stock_actual", "desconocido")
                        contexto_interno = f"Dile al usuario que si tenemos {nombre}. Cuesta {precio} euros y quedan {stock} unidades."
                    else:
                        contexto_interno = f"Dile al usuario que lo sientes, pero no hay {item} en stock actualmente."
                else:
                    contexto_interno = "El usuario pregunta por un producto de la tienda pero no esta claro cual es. Pide que lo repita."
            else:
                contexto_interno = "No has entendido la peticion del supermercado. Pide que lo repita de forma clara."

        # --- CAPA SENSORIAL B: ESCUELA (UAB) ---
        elif self.modo_entorno == "escuela":
            if (intent == "unknown" or item == "producto desconocido") and group and self.memoria_escuela["tema_pendiente"]:
                item = self.memoria_escuela["tema_pendiente"]
                intent = "schedule_query"

            if intent == "chat":
                contexto_interno = "Estas en la universidad UAB. El usuario charla de forma informal. Responde como un guia simpatico."
            elif intent == "location_query":
                coords = self.sql.get_classroom_location(item)
                if coords:
                    contexto_interno = f"Dile al usuario de forma muy breve que le muestras la ubicacion del aula {item} en el mapa."
                    aula_objetivo = item
                    lat_objetivo = coords['latitud']
                    lng_objetivo = coords['longitud']
                else:
                    contexto_interno = f"Dile al usuario que no tienes las coordenadas del aula '{item}' registradas en la base de datos de la UAB." 
            elif intent == "schedule_query":
                if item == "producto desconocido" and not time_val:
                    contexto_interno = "Pregunta por horarios pero faltan datos de la asignatura o la hora. Pidele amablemente algun dato mas."
                else:
                    info_clases = self.sql.get_school_info(item, group, time_val)
                    if not info_clases:
                        contexto_interno = f"No hay resultados de clases para '{item}'. Dile de forma amable que no encuentras esa clase hoy."
                        self.memoria_escuela["tema_pendiente"] = None
                    elif len(info_clases) > 1 and item != "producto desconocido" and not group and not time_val:
                        grupos_disp = ", ".join([str(c.get('grupo', '')) for c in info_clases if c.get('grupo')])
                        contexto_interno = f"Hay varios grupos disponibles ({grupos_disp}) para {item}. Pregunta de que grupo es."
                        self.memoria_escuela["tema_pendiente"] = item 
                    else:
                        lista_res = ", ".join([f"{c['asignatura']} en {c['aula']} a las {c['hora_inicio']}" for c in info_clases])
                        contexto_interno = f"Horario localizado: {lista_res}."
                        self.memoria_escuela["tema_pendiente"] = None
                        aula_objetivo = info_clases[0].get('aula')
                        lat_objetivo = info_clases[0].get('latitud')
                        lng_objetivo = info_clases[0].get('longitud')
            else:
                contexto_interno = "No has entendido la consulta universitaria. Pide educadamente que lo repita."

        # 2. Generar respuesta final estructurada y capturar EMOCIÓN
        resultado_emocional = self.nlp.generate_response(texto_usuario, contexto_interno)
        respuesta_natural = resultado_emocional.get("texto")
        
        # LÓGICA DE PRIORIDAD EMOCIONAL
        emocion_ojos = resultado_emocional.get("emocion", "neutral")
        if emocion_ojos == "neutral" and emocion_intent and emocion_intent != "neutro":
            emocion_ojos = emocion_intent

        print(f"[PlannerCloud] Emoción final inyectada en la respuesta: -> {emocion_ojos.upper()} <-")

        # 3. Devolvemos el diccionario definitivo al HRI de la Raspberry usando la función auxiliar
        return crear_respuesta_cloud(
            texto=respuesta_natural,
            estado_actual=self.estado_actual,
            emocion=emocion_ojos,
            lista_compra=self.lista_compra,
            intent=intent,
            aula=aula_objetivo,
            lat=lat_objetivo,
            lng=lng_objetivo
        )
