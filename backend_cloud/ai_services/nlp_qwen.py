# ai_services/nlp_qwen.py
import json
from openai import OpenAI
from core.prompts import PROMPT_SUPERMERCADO, PROMPT_ESCUELA, PROMPT_GENERACION_RESPUESTA
from core.config import Config

class NLPQwen:
    def __init__(self):
        self.uab_token = Config.UAB_TOKEN
        try:
            self.client = OpenAI(api_key="accesoAlLLM", base_url="https://dcc-llm.uab.cat/bes2/v1")
            print("[NLPQwen] Motor de Comprensión inicializado.")
        except Exception as e:
            print(f"[NLPQwen] Error de inicialización: {e}")
            self.client = None
    
    def parse_intent(self, text: str, modo: str = "supermercado"):
        # Elegimos la personalidad según el entorno del robot
        sistema_actual = PROMPT_SUPERMERCADO if modo == "supermercado" else PROMPT_ESCUELA
        
        if not self.client:
            return "unknown", None, 1, None, None, "Mis sistemas lógicos están apagados."
        
        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[
                    {"role": "system", "content": sistema_actual},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            raw_text = response.choices[0].message.content.strip()
            
            print("\n" + "="*15)
            print(f"[parse_intent RAW]:\n{raw_text}")
            print("="*15 + "\n")
            
            # Limpieza del bloque de código JSON por seguridad
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
                    
            data = json.loads(raw_text)
            
            intent = data.get("intent", "unknown")
            item = data.get("item", None)
            quantity = data.get("quantity", 1)
            group = data.get("group", None)
            time_val = data.get("time", None) 
            reply = data.get("reply", None)
            emocion = data.get("emocion", "neutro")
            
            return intent, item, quantity, group, time_val, reply, emocion

        except Exception as e:
            print(f"[NLPQwen] Error en parsing de intención: {e}")
            return "unknown", None, 1, None, None, "Fallo al procesar mi matriz lógica.", "triste"

    def generate_response(self, user_text: str, context: str) -> dict:
        """
        Genera un diccionario con la respuesta natural y la emoción correspondiente para los ojos.
        Devuelve: {"texto": str, "emocion": str}
        """
        if not self.client:
            return {"texto": "Lo siento, mi procesador cognitivo está desconectado.", "emocion": "triste"}

        paquete_usuario = f'Petición del usuario: "{user_text}"\nContexto interno del sistema: "{context}"'
        
        try:
            response = self.client.chat.completions.create(
                model="Modelo-bXs2",
                messages=[
                    {"role": "system", "content": PROMPT_GENERACION_RESPUESTA},
                    {"role": "user", "content": paquete_usuario}
                ],
                temperature=0.4
            )
            
            raw_text = response.choices[0].message.content.strip()
            
            print("\n" + "="*15)
            print(f"[generate_response RAW]:\n{raw_text}")
            print("="*15 + "\n")
            
            if "```" in raw_text:
                raw_text = raw_text.split("```")[1].strip()
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
            
            data = json.loads(raw_text)
            return {
                "texto": data.get("texto", "Procesamiento completado."),
                "emocion": data.get("emocion", "neutral")
            }
            
        except Exception as e:
            print(f"[NLPQwen] Error en generación emocional: {e}")
            return {
                "texto": "He ejecutado la tarea correctamente, pero tengo interferencias en mi expresión facial.",
                "emocion": "duda"
            }