# ai_services/vision_qwen.py
from openai import OpenAI
from core.prompts import PROMPT_VISION_ESTRICTO, PROMPT_VISION_ABIERTO
from core.config import Config

class VisionQwen:
    def __init__(self):
        self.uab_token = Config.UAB_TOKEN
        try:
            self.client = OpenAI(api_key=self.uab_token, base_url="https://dcc-llm.uab.cat/bes2/v1")
            print("[VisionQwen] Motor Visual Multimedia inicializado.")
        except Exception as e:
            print(f"[VisionQwen] Error conectando a las cámaras de la IA: {e}")
            self.client = None

    def identify_product(self, base64_image, mime_type="image/jpeg"):
        if not self.client: return "desconocido"
        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": PROMPT_VISION_ESTRICTO},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]}],
                temperature=0.01
            )
            return response.choices[0].message.content.strip().lower()
        except:
            return "desconocido"

    def visual_chat(self, base64_image, user_text, mime_type="image/jpeg"):
        if not self.client: return "Mis ojos virtuales no logran conectar con la red."
        try:
            prompt = PROMPT_VISION_ABIERTO.format(user_text=user_text)
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]}],
                temperature=0.4
            )
            return response.choices[0].message.content.strip()
        except:
            return "Perdona, me ha entrado algo en la lente y no logro enfocar bien."