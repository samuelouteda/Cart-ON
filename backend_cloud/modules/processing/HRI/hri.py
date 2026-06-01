import json
from openai import OpenAI

class HRINode:
    """
    Módulo NLP impulsado por la UAB (Qwen).
    Traduce el lenguaje natural a un JSON de intenciones.
    """
    def __init__(self):
        # ⚠️ PON AQUÍ TU TOKEN REAL DE LA UAB
        self.uab_token = "accesoAlLLM"
        
        try:
            self.client = OpenAI(
                api_key=self.uab_token, 
                base_url="https://dcc-llm.uab.cat/bes2/v1"
            )
            print("[HRINode] 🧠 Motor NLP (UAB Qwen) inicializado correctamente.")
        except Exception as e:
            print(f"[HRINode] 🔴 Error crítico al inicializar la IA de la UAB: {e}")
            self.client = None

    def parse_intent(self, raw_text: str):
        if not self.client:
            return "unknown", None, 1, "Mis sistemas lógicos están apagados."

        prompt = f"""
        Eres el cerebro lógico de Cart-ON, un robot de supermercado y AMR (Autonomous Mobile Robot).
        Analiza la petición del usuario y extrae la intención final.
        
        Intenciones válidas: 
        - "add" (añadir producto a la lista de la compra)
        - "delete" (quitar/borrar producto de la lista)
        - "read_list" (leer qué productos hay en la lista)
        - "read_stock" (preguntar por stock/precio de un producto)
        - "check_availability" (comprobar si la lista está disponible)
        - "clear" (vaciar toda la lista)
        - "start_mapping" (fase 1: iniciar modo de mapeo/auditoría)
        - "stop_mapping" (detener el modo de mapeo)
        - "start_assistance" (fase 3: empezar a guiar al usuario)
        - "chat" (saludos, preguntas generales, interacción social)
        - "unknown" (ruido o peticiones imposibles)

        Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta, sin texto adicional ni formato Markdown:
        {{"intent": "valor", "quantity": 1, "item": "nombre", "reply": "respuesta"}}
        
        Reglas:
        1. Si la intención es "chat", en "reply" escribe una respuesta amigable y breve (máx 2 frases). Si no, "reply" es null.
        2. Si el usuario usa pronombres ("esto", "eso"), pon "esto" en el campo item.
        3. Si no hay producto claro, "item" es null. Si no hay cantidad, "quantity" es 1.

        Petición del usuario: "{raw_text}"
        """

        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[
                    {"role": "system", "content": "Eres un parseador estricto que solo devuelve JSON puro."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1 # Temperatura casi a 0 para que no invente ni añada texto extra
            )
            
            texto_crudo = response.choices[0].message.content.strip()
            
            # Limpieza por si Qwen añade etiquetas Markdown de código (```json ... ```)
            texto_limpio = texto_crudo.replace("```json", "").replace("```", "").strip()
            
            datos = json.loads(texto_limpio)
            
            intent = datos.get("intent", "unknown")
            item = datos.get("item", None)
            reply = datos.get("reply", None)
            
            try:
                quantity = int(datos.get("quantity", 1))
            except (ValueError, TypeError):
                quantity = 1
                
            return intent, item, quantity, reply

        except Exception as e:
            print(f"[HRINode] 🔴 ERROR parseando intención con Qwen (UAB): {e}")
            return "unknown", None, 1, "Ha habido un error al procesar tu petición en los servidores de la UAB."