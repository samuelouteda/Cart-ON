from openai import OpenAI

class VisionAPI:
    """
    Módulo de Percepción Visual impulsado por la UAB (Qwen).
    Se encarga de analizar imágenes, ya sea para escanear productos o para charlar.
    """
    def __init__(self):
        # ⚠️ PON AQUÍ TU TOKEN REAL DE LA UAB
        self.uab_token = "accesoAlLLM"
        
        try:
            self.client = OpenAI(
                api_key=self.uab_token, 
                base_url="https://dcc-llm.uab.cat/bes2/v1"
            )
            print("[VisionAPI] 👁️ Motor Visual (UAB Qwen) inicializado correctamente.")
        except Exception as e:
            print(f"[VisionAPI] 🔴 Error crítico al inicializar la visión de la UAB: {e}")
            self.client = None

    def identify_product(self, base64_image, mime_type="image/jpeg"):
        """
        Fase de Escaneo / Búsqueda en BD:
        Intenta identificar de forma estricta qué producto es para buscarlo en Cloud SQL.
        """
        if not self.client:
            return "desconocido"

        prompt_estricto = """
        Eres el sistema visual de un robot de supermercado. Dime qué producto ves.
        Responde ÚNICAMENTE con el nombre genérico del producto (ej: manzana, botella, leche, libro).
        Si es una imagen completamente negra o no logras distinguir nada claro, responde exactamente: desconocido.
        No añadas puntos, ni frases extra.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_estricto},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }],
                temperature=0.1 # Muy frío para que sea preciso y no alucine
            )
            return response.choices[0].message.content.strip().lower()
        except Exception as e:
            print(f"[VisionAPI] 🔴 Error en reconocimiento estricto: {e}")
            return "desconocido"

    def visual_chat(self, base64_image, user_text, mime_type="image/jpeg"):
        """
        Fase de Interacción (HRI General):
        El usuario le enseña algo a la cámara y hace una pregunta o comentario abierto.
        """
        if not self.client:
            return "Ahora mismo tengo los sensores visuales desconectados, no puedo ver nada."

        prompt_abierto = f"""
        Eres Cart-ON, un simpático robot asistente de supermercado. 
        El humano te está enseñando algo por la cámara y te ha dicho esto: "{user_text}".
        Responde a su comentario basándote en lo que ves en la imagen. 
        Sé amigable, muy breve (1 o 2 frases máximo) y habla en un tono natural y servicial en español.
        """

        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_abierto},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }],
                temperature=0.4 # Un poco más creativo para que la charla sea natural
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[VisionAPI] 🔴 Error en chat visual: {e}")
            return "Perdona, me ha entrado algo en la lente de la cámara y no veo bien."