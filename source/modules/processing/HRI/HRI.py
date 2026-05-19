from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT

import requests
import base64

class HRI(BaseModule):
    """
    Layer 2: Human-Robot Interaction Module
    """

    # Class Attributes Definition
    _add_commands = ["añadir", "añade", "añádeme", "mete", "apunta", "pon"]
    _delete_commands = ["borrar", "borra", "quita", "elimina", "saca"]
    _read_commands = ["qué hay", "lee", "dime", "cuál es", "revisa", "muestra", "enseña"]
    _clear_commands = ["vaciar", "vacía", "limpia", "borra toda"]

    _filler_words = ["por", "favor", "porfa", "a", "en", "la", "lista", "quiero", "necesito", "el", "los", "las", "un", "una"]
    _containers = ["bote", "botes", "pote", "potes", "litro", "litros", "paquete", "paquetes", "botella", "botellas", "de"]

    _number_mapping = {
        "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, 
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10
    }

    def __init__(self, name, event_bus, shared_sensor_stream, api_key):

        super().__init__(name, event_bus)
        self.data_stream = shared_sensor_stream
        self.api_key = api_key

    def get_audio(self): 
        """Reads audio without consuming it"""
        return self.data_stream['audio']

    def consume_audio(self):
        """Consumes (deletes) the audio data"""
        self.data_stream['audio'] = None
    
    def read_audio(self):
        """Reads audio data and then consumes it"""
        audio = self.data_stream['audio']
        self.consume_audio()
        return audio
    
    

    def extract_quantity_and_product(self, spoken_text, command_list):
        # extrae entidades clave de la frase
        for command in command_list:
            spoken_text = spoken_text.replace(command, "")
            
        words = spoken_text.split()
        quantity = 1 
        product_words = []
        
        for word in words:
            if word.isdigit(): 
                quantity = int(word)
            elif word in self._number_mapping: 
                quantity = self._number_mapping[word]
            elif word not in self._filler_words and word not in self._containers:
                product_words.append(word)
                
        return quantity, " ".join(product_words).strip()

    def parse_intent(self, raw_text):
        # Cognitive logic to classify the requested action
        if any(command in raw_text for command in self._add_commands):
            quantity, item = self.extract_quantity_and_product(raw_text, self._add_commands)
            return "add", item, quantity
        elif any(command in raw_text for command in self._delete_commands):
            quantity, item = self.extract_quantity_and_product(raw_text, self._delete_commands)
            return "delete", item, quantity
        elif any(command in raw_text for command in self._read_commands):
            return "read", None, None
        elif any(command in raw_text for command in self._clear_commands):
            return "clear", None, None
            
        return "unknown", None, None

    def speech_to_text(self, audio_data):
        # Converts audio to text using Google's API
        audio_wav = audio_data.get_wav_data()
        audio_b64 = base64.b64encode(audio_wav).decode("utf-8")

        endpoint_url = f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}"
        payload = {
            "config": {"encoding": "LINEAR16", "sampleRateHertz": audio_data.sample_rate, "languageCode": "es-ES"},
            "audio": {"content": audio_b64}
        }

        try:
            response = requests.post(endpoint_url, json=payload)
            response_json = response.json()
            if "results" in response_json:
                return response_json["results"][0]["alternatives"][0]["transcript"].lower().strip()
        except Exception as e:
            print(f"SST Connection error: {e}")
        return None
    
    def text_to_speech(self, text_to_say):
        # genera los bytes de audio a partir de texto (modulo cognitivo puro, no reproduce)
        endpoint_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"

        payload = {
            "input": {"text": text_to_say},
            "voice": {"languageCode": "es-ES", "name": "es-ES-Neural2-F"},
            "audioConfig": {"audioEncoding": "MP3"}
        }

        try:
            response = requests.post(endpoint_url, json=payload)
            response_json = response.json()
            
            if "audioContent" in response_json:
                # decodificamos la respuesta a bytes puros y la retornamos
                return base64.b64decode(response_json["audioContent"])
        except Exception as e:
            print(f"TTS Petition error: {e}")
            
        return None
    
    def process_audio(self):
        audio_data = self.read_audio()
        print(f"{INDENT_OUTPUT}[{self.name}] Listening...")

        if not audio_data:
            return

        

        raw_text = self.speech_to_text(audio_data)
        
            
        if not raw_text:
            return
        
        print(f"{INDENT_OUTPUT}[{self.name}] Audio detected: \"{raw_text}\"")

        # Process audio
        intent, item, quantity = self.parse_intent(raw_text)

        if intent == "unknown":
            print(f"{INDENT_OUTPUT}[{self.name}] Unknown order. Ignoring input.")
            return
    
        self.publish_event(
            Event(
                type="voice_command",
                data={
                    "intent": intent,
                    "item": item,
                    "quantity": quantity,
                    "raw_text": raw_text
                },
                origin=self.name
            )
        )

            
    
    def handle_task(self, task):
        if task.type == "speak":
            # Play audio to talk back
            print(f"    [{self.name}] Playing audio.")

    def speak(self, text):
        # el planificador orquesta la comunicacion: pide el audio a hri y se lo pasa a actuacion
        print(f"{INDENT_OUTPUT}[{self.name}] Robot: {text}")
        audio_bytes = self.text_to_speech(text, self.api_key)
        # if audio_bytes:
        #     speaker.play_audio(audio_bytes)

    def loop(self):
        self.process_audio()


            