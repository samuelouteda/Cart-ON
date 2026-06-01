from modules.processing.data.sql_manager import SQLManager
from modules.processing.HRI.hri import HRINode
from modules.processing.perception.vision_api import VisionAPI

class PlannerCloud:
    """
    State Manager & Decision Making (Cloud).
    Controla en qué fase está el robot y coordina los microservicios.
    """
    def __init__(self):
        print("[Planner] ⚙️ Iniciando el Cerebro Central en la Nube...")
        self.sql = SQLManager()
        self.nlp = HRINode()
        self.vision = VisionAPI()
        
        # El robot arranca por defecto en la Fase 2 (estacionado, listo para hablar)
        self.estado_actual = "fase_2_interaccion"

    def procesar_peticion_hri(self, texto_usuario: str, imagen_bytes: bytes, mime_type: str = "image/jpeg"):
        """
        Punto de entrada para la FASE 2. 
        Recibe texto e imagen de la Raspberry, decide qué hacer y devuelve la orden.
        """
        # 1. Sacar la intención con Qwen NLP
        intent, item, quantity, reply = self.nlp.parse_intent(texto_usuario)
        
        # 2. GESTIÓN DE ESTADOS (Transiciones)
        if intent == "start_mapping":
            self.estado_actual = "fase_1_escaneo"
            return {"status": "success", "intent": intent, "comando_robot": "START_SLAM", "texto": "Iniciando protocolo de mapeo y auditoría visual. Motores en marcha."}
            
        elif intent == "start_assistance":
            self.estado_actual = "fase_3_asistencia"
            return {"status": "success", "intent": intent, "comando_robot": "START_NAVIGATION", "texto": "Por supuesto. Sígueme, te llevaré a por los productos de tu lista."}
            
        elif intent == "stop_mapping":
            self.estado_actual = "fase_2_interaccion"
            return {"status": "success", "intent": intent, "comando_robot": "STOP_MOTORS", "texto": "Mapeo detenido. Me quedo a la espera de tus instrucciones."}

        # 3. CHAT GENERAL (Con o sin visión)
        if intent == "chat":
            # Si el usuario pregunta algo visual (y la foto pesa más de 5KB para descartar la foto negra falsa)
            if imagen_bytes and len(imagen_bytes) > 5000 and any(palabra in texto_usuario.lower() for palabra in ["mira", "esto", "enseño", "qué", "color"]):
                respuesta_visual = self.vision.visual_chat(imagen_bytes, texto_usuario, mime_type)
                return {"status": "success", "intent": intent, "texto": respuesta_visual}
            else:
                return {"status": "success", "intent": intent, "texto": reply if reply else "Hola, ¿en qué te puedo ayudar hoy?"}

        # 4. GESTIÓN DE PRODUCTOS Y SQL
        respuesta_robot = ""
        acciones_tienda = ["read", "read_stock", "add", "delete", "check_availability"]
        
        if intent in acciones_tienda:
            # Si dice "esto", usamos la cámara para saber qué es "esto"
            if item == "esto" or not item:
                if imagen_bytes and len(imagen_bytes) > 5000:
                    item = self.vision.identify_product(imagen_bytes, mime_type)
                else:
                    return {"status": "success", "intent": "unknown", "texto": "Me hablas de un producto, pero no me has dicho cuál y no tengo la cámara activada para verlo."}
            
            # Una vez sabemos el item real, consultamos al SQL
            info_producto = self.sql.get_product_info(item)
            
            if info_producto:
                if intent in ["read", "read_stock"]:
                    respuesta_robot = f"He detectado {info_producto['nombre_pantalla']}. Su precio es de {info_producto['precio']} euros y tenemos {info_producto['stock_actual']} en stock."
                elif intent == "add":
                    respuesta_robot = f"Anotado. He añadido {quantity} de {info_producto['nombre_pantalla']} a tu lista."
                    # TODO: Llamar a self.sql.add_to_list()
            else:
                if item == "desconocido":
                    respuesta_robot = "No logro distinguir bien qué producto me estás enseñando. ¿Puedes acercarlo un poco?"
                else:
                    respuesta_robot = f"Lo siento, he buscado '{item}' en nuestra base de datos pero no lo encuentro."

        elif intent == "unknown":
            respuesta_robot = "Perdona, no he procesado bien tu solicitud."
            
        else:
            respuesta_robot = f"Entiendo que quieres hacer {intent} con {item}, pero esa función aún no está activa."

        return {
            "status": "success",
            "intent": intent,
            "producto": item,
            "cantidad": quantity,
            "texto": respuesta_robot,
            "estado_actual": self.estado_actual
        }