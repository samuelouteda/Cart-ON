import json
from google import genai
from google.genai import types

class HRI:
    """
    Cerebro NLP (Nube). 
    Versión aislada para Google Cloud. Usando el nuevo SDK 'google.genai'.
    """
    def __init__(self, name, event_bus, shared_sensor_stream, stt_tts_api_key, gemini_api_key):
        self.name = name
        print(f"[{self.name}] 🧠 Inicializando motor NLP Gemini (Nuevo SDK) en el servidor Cloud...")
        # 🚀 NUEVA SINTAXIS: Se crea un cliente instanciado
        self.client = genai.Client(api_key=gemini_api_key)

    def parse_intent(self, raw_text):
        prompt = f"""
        Eres la IA de un amigable robot asistente de supermercado.
        Analiza la petición del usuario y extrae la intención final.
        
        Intenciones válidas: 
        - "add" (añadir producto a la lista de la compra)
        - "delete" (quitar/borrar producto de la lista de la compra)
        - "read_list" (leer qué productos hay apuntados en la lista)
        - "read_stock" (preguntar por el stock/inventario de un producto en la tienda)
        - "check_availability" (comprobar si los productos de mi lista están disponibles en la tienda)
        - "clear" (vaciar toda la lista de la compra)
        - "start_mapping" (iniciar modo de mapeo/auditoría con la cámara)
        - "stop_mapping" (detener el modo de mapeo)
        - "chat" (saludos, insultos, preguntas sobre ti o charla general)
        - "unknown" (ruido sin sentido)

        Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:
        {{"intent": "valor", "quantity": numero_entero, "item": "nombre_del_producto", "reply": "respuesta conversacional"}}
        
        Reglas estrictas:
        1. Si la intención es "chat", en el campo "reply" debes escribir una respuesta amigable, muy breve y natural en español (máximo 2 frases).
        2. Si la intención NO es "chat", el campo "reply" debe ser null.
        3. Si no hay un producto claro, "item" es null. Si no especifica cantidad, "quantity" es 1.

        Petición del usuario: "{raw_text}"
        """
        try:
            # 🚀 NUEVA SINTAXIS: Llamada a la API a través de client.models
            respuesta = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            datos = json.loads(respuesta.text)
            print(f"[{self.name}] Gemini entendió: {datos}")
            
            intent = datos.get("intent", "unknown")
            item = datos.get("item", None)
            reply = datos.get("reply", None)
            
            try:
                quantity = int(datos.get("quantity", 1))
            except (ValueError, TypeError):
                quantity = 1
                
            return intent, item, quantity, reply

        except Exception as e:
            print(f"[{self.name}] 🔴 ERROR en Gemini NLP: {e}")
            return "unknown", None, 1, None