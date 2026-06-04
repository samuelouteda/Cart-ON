import unicodedata
from db.sql_manager import SQLManager
from ai_services.nlp_qwen import NLPQwen
from ai_services.vision_qwen import VisionQwen

# Función para quitar tildes y estandarizar nombres
def limpiar_nombre(texto):
    if not texto: return "producto desconocido"
    texto_sin_tildes = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto_sin_tildes.lower().strip()

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
        
        # 🕹️ COMANDOS DE CAMBIO DE MODO (Hardcodeados para que sean instantáneos)
        texto_bajo = texto_usuario.lower()
        if "modo escuela" in texto_bajo:
            self.modo_entorno = "escuela"
            return {"status": "success", "texto": "Modo escuela activado. Ahora soy tu guía universitario de la UAB."}
        elif "modo supermercado" in texto_bajo:
            self.modo_entorno = "supermercado"
            return {"status": "success", "texto": "Modo supermercado activado. Listo para hacer la compra."}

        # Analizamos el texto usando el cerebro correspondiente
        intent, item_crudo, quantity, group, time_val, reply = self.nlp.parse_intent(texto_usuario, modo=self.modo_entorno)
        item = limpiar_nombre(item_crudo)
        contexto_interno = ""

        # --- RECUPERACIÓN DE MEMORIA ESCUELA ---
        if self.modo_entorno == "escuela" and (intent == "unknown" or item == "producto desconocido") and group and self.memoria_escuela["tema_pendiente"]:
            item = self.memoria_escuela["tema_pendiente"]
            intent = "schedule_query" 

        # --- A. BLOQUE SUPERMERCADO ---
        if self.modo_entorno == "supermercado":
            if intent == "chat":
                contexto_interno = "El usuario charla. Responde de forma amistosa y rápida."
            # ... (Aquí va tu código de siempre: add, delete, read_list, read_stock...)
            
        # --- B. BLOQUE ESCUELA (UAB) ---
        elif self.modo_entorno == "escuela":
            if intent == "chat":
                contexto_interno = "El usuario charla. Responde como un guía simpático de la universidad."
                
            elif intent == "schedule_query":
                if item == "producto desconocido" and not time_val:
                    contexto_interno = "El usuario pregunta por horarios pero no te ha dicho ni la asignatura ni la hora. Pídele algún dato para buscar."
                else:
                    info_clases = self.sql.get_school_info(item, group, time_val)
                    
                    if not info_clases:
                        # 🔴 INSTRUCCIÓN ESTRICTA ANTI-ALUCINACIONES
                        contexto_interno = f"Has buscado en la base de datos de la UAB y NO HAY RESULTADOS. Dile al usuario, de forma amable, que no encuentras esa asignatura u horario en la base de datos de la universidad. NO te inventes horarios."
                    else:
                        lista_res = ", ".join([f"{c['asignatura']} en {c['aula']} a las {c['hora_inicio']}" for c in info_clases])
                        contexto_interno = f"Info UAB: dile al usuario que tienes estas clases programadas: {lista_res}."


        # Generar voz final usando el contexto de lo que ha pasado
        respuesta_natural = self.nlp.generate_response(texto_usuario, contexto_interno)
        return {"status": "success", "texto": respuesta_natural, "estado_actual": self.estado_actual}