import os
from ai_services.nlp_qwen import NLPQwen
from db.sql_manager import SQLManager

# Función auxiliar para limpiar el nombre
def limpiar_nombre(texto):
    if not texto:
        return "producto desconocido"
    return texto.lower().strip()

class PlannerCloud:
    def __init__(self):
        print("[PlannerCloud] ⚙️ Orquestador Dual iniciado.")
        self.sql = SQLManager()
        self.nlp = NLPQwen()
        self.estado_actual = "fase_2_interaccion"
        
        # Variables de estado
        self.modo_entorno = "supermercado" # Empieza por defecto en el súper
        self.lista_compra = {}
        self.memoria_escuela = {"tema_pendiente": None}

    def procesar_peticion_hri(self, texto_usuario: str, imagen_bytes: bytes, mime_type: str = "image/jpeg"):
        
        # 🕹️ COMANDOS DE CAMBIO DE MODO (Instantáneos por voz)
        texto_bajo = texto_usuario.lower()
        if "modo escuela" in texto_bajo:
            self.modo_entorno = "escuela"
            return {"status": "success", "texto": "Modo escuela activado. Ahora soy tu guía universitario de la UAB.", "estado_actual": self.estado_actual}
        elif "modo supermercado" in texto_bajo:
            self.modo_entorno = "supermercado"
            return {"status": "success", "texto": "Modo supermercado activado. Listo para hacer la compra.", "estado_actual": self.estado_actual}
        elif "modo" in texto_bajo and "cambia" in texto_bajo:
            # 🛡️ CORTAFUEGOS
            return {"status": "success", "texto": "Solo dispongo de dos modos: Modo Escuela y Modo Supermercado. Por favor, dime cuál prefieres.", "estado_actual": self.estado_actual}

        # 1. Analizamos el texto (Con bloque blindado anti-crashes)
        resultado_nlp = self.nlp.parse_intent(texto_usuario, modo=self.modo_entorno)
        
        if len(resultado_nlp) == 6:
            intent, item_crudo, quantity, group, time_val, reply = resultado_nlp
        elif len(resultado_nlp) == 5:
            intent, item_crudo, group, time_val, reply = resultado_nlp
            quantity = 1 
        else:
            intent, item_crudo, quantity, group, time_val, reply = "unknown", "producto desconocido", 1, None, None, None

        item = limpiar_nombre(item_crudo)
        contexto_interno = ""

        # Variables para inicializar el mapa multimedia
        aula_objetivo = None
        lat_objetivo = None
        lng_objetivo = None

        # --- A. BLOQUE SUPERMERCADO ---
        if self.modo_entorno == "supermercado":
            if intent == "chat":
                contexto_interno = "Estás en el supermercado. El usuario charla. Responde de forma amistosa."
            
            elif intent == "add":
                if item != "producto desconocido":
                    cantidad_final = quantity if quantity else 1
                    self.lista_compra[item] = self.lista_compra.get(item, 0) + cantidad_final
                    contexto_interno = f"Confirma amablemente que has añadido {cantidad_final} de {item} a la lista de la compra."
                else:
                    contexto_interno = "El usuario quiere añadir algo a la lista pero no has entendido qué producto es. Pídele que lo repita."
                    
            elif intent == "delete":
                if item in self.lista_compra:
                    del self.lista_compra[item]
                    contexto_interno = f"Confirma que has quitado {item} de la lista de la compra."
                else:
                    contexto_interno = f"Dile al usuario que {item} no estaba en su lista de la compra."
                    
            elif intent == "read_list":
                if self.lista_compra:
                    productos = ", ".join([f"{cant} de {prod}" for prod, cant in self.lista_compra.items()])
                    contexto_interno = f"Dile al usuario que en su lista de la compra tiene: {productos}."
                else:
                    contexto_interno = "Dile al usuario que su lista de la compra está vacía actualmente."
                    
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
                        contexto_interno = f"Dile al usuario que sí tenemos {nombre}. Cuesta {precio} euros y quedan {stock} unidades en stock."
                    else:
                        contexto_interno = f"Dile al usuario que lo sientes, pero no tenemos {item} en el supermercado actualmente."
                else:
                    contexto_interno = "El usuario pregunta por un producto pero no te ha quedado claro cuál es. Pide que lo repita."
            else:
                contexto_interno = "No has entendido la petición del supermercado. Pide que lo repita."


        # --- B. BLOQUE ESCUELA (UAB) ---
        elif self.modo_entorno == "escuela":
            # Recuperación de memoria si estábamos esperando respuesta de un grupo
            if (intent == "unknown" or item == "producto desconocido") and group and self.memoria_escuela["tema_pendiente"]:
                item = self.memoria_escuela["tema_pendiente"]
                intent = "schedule_query"

            if intent == "chat":
                contexto_interno = "Estás en la universidad UAB. El usuario charla. Responde como un guía simpático."
            
            elif intent == "location_query":
                coords = self.sql.get_classroom_location(item)
                if coords:
                    contexto_interno = f"Dile al usuario de forma muy breve que le muestras la ubicación del aula {item} en la pantalla."
                    aula_objetivo = item
                    lat_objetivo = coords['latitud']
                    lng_objetivo = coords['longitud']
                else:
                    contexto_interno = f"Estás en la universidad UAB. Dile al usuario que no tienes las coordenadas del aula '{item}' registradas en tu sistema." 
            
            elif intent == "schedule_query":
                if item == "producto desconocido" and not time_val:
                    contexto_interno = "Estás en la UAB. El usuario pregunta por horarios pero no te ha dicho ni la asignatura ni la hora. Pídele algún dato para buscar."
                else:
                    info_clases = self.sql.get_school_info(item, group, time_val)
                    
                    if not info_clases:
                        contexto_interno = f"Estás en la universidad UAB. Has buscado en la base de datos y NO HAY RESULTADOS para '{item}'. Dile al usuario, de forma amable, que no encuentras esa clase. NO menciones el supermercado ni inventes horarios."
                        self.memoria_escuela["tema_pendiente"] = None
                    
                    elif len(info_clases) > 1 and item != "producto desconocido" and not group and not time_val:
                        grupos_disp = ", ".join([str(c.get('grupo', '')) for c in info_clases if c.get('grupo')])
                        contexto_interno = f"Estás en la UAB. Hay varios grupos para {item}: {grupos_disp}. Pide al usuario que te diga de qué grupo es."
                        self.memoria_escuela["tema_pendiente"] = item 
                    
                    else:
                        lista_res = ", ".join([f"{c['asignatura']} en {c['aula']} a las {c['hora_inicio']}" for c in info_clases])
                        contexto_interno = f"Info UAB: dile al usuario que tienes estas clases programadas: {lista_res}."
                        self.memoria_escuela["tema_pendiente"] = None
                        
                        aula_objetivo = info_clases[0].get('aula')
                        lat_objetivo = info_clases[0].get('latitud')
                        lng_objetivo = info_clases[0].get('longitud')
            else:
                contexto_interno = "Estás en la universidad UAB. No has entendido la petición. Pide que lo repita de otra forma."

        # 2. Generar voz final usando el contexto estricto
        respuesta_natural = self.nlp.generate_response(texto_usuario, contexto_interno)
        
        # 3. Devolvemos el diccionario
        return {
            "status": "success", 
            "texto": respuesta_natural, 
            "estado_actual": self.estado_actual,
            "aula": aula_objetivo,
            "lat": lat_objetivo,
            "lng": lng_objetivo
        }