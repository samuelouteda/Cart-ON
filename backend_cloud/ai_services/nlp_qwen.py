# ai_services/nlp_qwen.py
import json
from openai import OpenAI
import json
from core.prompts import PROMPT_SUPERMERCADO, PROMPT_ESCUELA
from core.config import Config

class NLPQwen:
    def __init__(self):
        self.uab_token = Config.UAB_TOKEN
        try:
            self.client = OpenAI(api_key=self.uab_token, base_url="https://dcc-llm.uab.cat/bes2/v1")
            print("[NLPQwen] 🧠 Motor de Comprensión inicializado.")
        except Exception as e:
            print(f"[NLPQwen] 🔴 Error: {e}")
            self.client = None
    
    def parse_intent(self, text: str, modo: str = "supermercado"):
        # Elegimos la personalidad
        sistema_actual = PROMPT_SUPERMERCADO if modo == "supermercado" else PROMPT_ESCUELA
        
        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2", # O el que estés usando en UAB
                messages=[
                    {"role": "system", "content": sistema_actual},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            raw_text = response.choices[0].message.content.strip()
            
            # Limpieza del bloque de código JSON (por si Qwen devuelve ```json ... ```)
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
                    
            data = json.loads(raw_text)
            
            # Extracción segura: usamos .get() por si un JSON no tiene una clave concreta
            intent = data.get("intent", "unknown")
            item = data.get("item", None)
            quantity = data.get("quantity", 1)
            group = data.get("group", None)
            time_val = data.get("time", None) # Nuevo campo
            reply = data.get("reply", None)
            
            # Ahora devolvemos 6 variables
            return intent, item, quantity, group, time_val, reply


        except Exception as e:
            print(f"Error en NLP: {e}")
            return "unknown", None, 1, None, "Fallo al procesar."

        if not self.client:
            return "unknown", None, 1, "Mis sistemas lógicos están apagados."

        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[
                    {"role": "system", "content": "Eres un parseador estricto que solo devuelve JSON puro."},
                    {"role": "user", "content": PROMPT_NLP + f'\nPetición: "{raw_text}"'}
                ],
                temperature=0.01 
            )
            
            texto_crudo = response.choices[0].message.content.strip()
            texto_limpio = texto_crudo.replace("```json", "").replace("```", "").strip()
            datos = json.loads(texto_limpio)
            
            intent = datos.get("intent", "unknown")
            item = datos.get("item", None)
            reply = datos.get("reply", None)
            quantity = int(datos.get("quantity", 1)) if str(datos.get("quantity")).isdigit() else 1
                
            return intent, item, quantity, reply

        except Exception as e:
            print(f"[NLPQwen] 🔴 ERROR de parseo: {e}")
            return "unknown", None, 1, "Ha habido un error en mi cerebro central."
        
    def generate_response(self, user_text: str, context: str):
        """
        Genera una respuesta natural basada en lo que ha hecho el sistema por debajo.
        """
        prompt = f"""
        Eres Cart-ON, un robot asistente de supermercado muy amable y servicial.
        El usuario te ha dicho: "{user_text}"
        
        Tu sistema informático interno te informa de lo siguiente:
        "{context}"
        
        Basándote en esa información, respóndele al usuario de forma natural, conversacional y en español.
        No digas cosas como "mi sistema interno dice" ni hables como un robot leyendo una base de datos.
        Simplemente dale la información con naturalidad. Sé breve (1 o 2 frases máximo).
        """
        
        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6 # Un poco más alto para que sea más creativo y natural
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return "Perdona, he procesado lo que me has pedido pero tengo un fallo en mi módulo de voz."