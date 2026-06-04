import os
from ai_services.nlp_qwen import NLPQwen
from db.sql_manager import SQLManager

# Función auxiliar para limpiar el nombre si no viene en tus utils
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
            # 🛡️ CORTAFUEGOS: Si pide cambiar a un modo que no existe, lo cortamos en seco
            return {"status": "success", "texto": "Solo dispongo de dos modos: Modo Escuela y Modo Supermercado. Por favor, dime cuál prefieres.", "estado_actual": self.estado_actual}

        # 1. Analizamos el texto usando el cerebro correspondiente (Devuelve 6 variables)
        intent, item_crudo, quantity, group, time_val, reply = self.nlp.parse_intent(texto_usuario, modo=self.modo_entorno)
        item = limpiar_nombre(item_crudo)
        contexto_interno = ""

        # Variables para inicializar el mapa
        aula_objetivo = None
        lat_objetivo = None
        lng_objetivo = None

        # --- RECUPERACIÓN DE MEMORIA ESCUELA ---
        if self.modo_entorno == "escuela" and (intent == "unknown" or item == "producto desconocido") and group and self.memoria_escuela["tema_pendiente"]:
            item = self.memoria_escuela["tema_pendiente"]
            intent = "schedule_query" 

        # --- A. BLOQUE SUPERMERCADO ---
        if self.modo_entorno == "supermercado":
            if intent == "chat":
                contexto_interno = "El usuario charla. Responde de forma amistosa y rápida."
            
            # ---> (AQUÍ DEBES DEJAR TU LÓGICA DE SUPERMERCADO DE SIEMPRE: add, delete, read_list, read_stock...)
            
        # --- B. BLOQUE ESCUELA (UAB) ---
        elif self.modo_entorno == "escuela":
            if intent == "chat":
                contexto_interno = "El usuario charla. Responde como un guía simpático de la universidad."
            
            elif intent == "location_query":
                # Nueva intención: buscar solo el aula
                coords = self.sql.get_classroom_location(item)
                if coords:
                    contexto_interno = f"Dile al usuario de forma muy breve que le muestras la ubicación del aula {item} en la pantalla."
                    aula_objetivo = item
                    lat_objetivo = coords['latitud']
                    lng_objetivo = coords['longitud']
                else:
                    contexto_interno = f"Dile al usuario que no tienes las coordenadas del aula '{item}' registradas en tu sistema." 
            
            elif intent == "schedule_query":
                # Si no dice NI asignatura NI hora, no podemos buscar nada
                if item == "producto desconocido" and not time_val:
                    contexto_interno = "El usuario pregunta por horarios pero no te ha dicho ni la asignatura ni la hora. Pídele algún dato para buscar."
                else:
                    # Buscamos en la BD usando lo que tengamos (el SQLManager ahora hace el LEFT JOIN)
                    info_clases = self.sql.get_school_info(item, group, time_val)
                    
                    if not info_clases:
                        # 🔴 INSTRUCCIÓN ESTRICTA ANTI-ALUCINACIONES
                        contexto_interno = f"Has buscado en la base de datos de la UAB y NO HAY RESULTADOS para la asignatura '{item}' u hora '{time_val}'. Dile al usuario, de forma amable, que no encuentras esa clase. NO te inventes horarios."
                        self.memoria_escuela["tema_pendiente"] = None
                    
                    elif len(info_clases) > 1 and item != "producto desconocido" and not group and not time_val:
                        # Hay varias clases de la misma asignatura (ej. distintos grupos). Pedimos aclaración.
                        grupos_disp = ", ".join([str(c.get('grupo', '')) for c in info_clases if c.get('grupo')])
                        contexto_interno = f"Hay varios grupos para {item}: {grupos_disp}. Pide al usuario que te diga de qué grupo es."
                        self.memoria_escuela["tema_pendiente"] = item 
                    
                    else:
                        # Hay una (o varias, si pediste hora general), listamos las clases encontradas
                        lista_res = ", ".join([f"{c['asignatura']} en {c['aula']} a las {c['hora_inicio']}" for c in info_clases])
                        contexto_interno = f"Info UAB: dile al usuario que tienes estas clases programadas: {lista_res}."
                        self.memoria_escuela["tema_pendiente"] = None
                        
                        # 📍 GUARDAMOS EL AULA Y SUS COORDENADAS PARA EL MAPA MULTIMEDIA
                        # Cogemos los datos del primer resultado de la lista
                        aula_objetivo = info_clases[0].get('aula')
                        lat_objetivo = info_clases[0].get('latitud')
                        lng_objetivo = info_clases[0].get('longitud')

        # 2. Generar voz final usando el contexto estricto
        respuesta_natural = self.nlp.generate_response(texto_usuario, contexto_interno)
        
        # 3. Devolvemos el diccionario incluyendo el estado y los datos de geolocalización
        return {
            "status": "success", 
            "texto": respuesta_natural, 
            "estado_actual": self.estado_actual,
            "aula": aula_objetivo,
            "lat": lat_objetivo,
            "lng": lng_objetivo
        }