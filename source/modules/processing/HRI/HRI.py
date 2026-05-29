from core.base_module import BaseModule
from core.event import Event
from core.constants import INDENT_OUTPUT
from core.task import Task
from modules.actuation.speaker import Speaker
from modules.actuation.display import Display

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
    # AFEGIR JUNTAMENT AMB ELS ALTRES ATRIBUTS DE CLASSE DE VOCABULARI
    _shutdown_commands = ["cerrar", "apagar", "desconectar", "salir", "terminar", "apágate", "muerete", "boom"]
    
    _filler_words = ["por", "favor", "porfa", "a", "en", "la", "lista", "quiero", "necesito", "el", "los", "las", "un", "una"]
    _containers = ["bote", "botes", "pote", "potes", "litro", "litros", "paquete", "paquetes", "botella", "botellas", "de"]

    _number_mapping = {
        "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, 
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10
    }

    def __init__(self, name, event_bus, shared_sensor_stream, api_key, data_task_bus, shared_data):

        super().__init__(name, event_bus)
        self.sensor_stream = shared_sensor_stream
        self.api_key = api_key

        self.data_task_bus = data_task_bus
        self.shared_data = shared_data
        self.speaker = Speaker("Speaker", event_bus, shared_data)
        self.display = Display("Display", event_bus, shared_data)

    def get_audio(self): 
        """Reads audio without consuming it"""
        return self.sensor_stream['audio']

    def consume_audio(self):
        """Consumes (deletes) the audio data"""
        self.sensor_stream['audio'] = None
    
    def read_audio(self):
        """Reads audio data and then consumes it"""
        audio = self.sensor_stream['audio']
        self.consume_audio()
        return audio
    
    def add_data_task(self, task):
        self.data_task_bus.put(task)
    

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
        elif any(command in raw_text for command in self._shutdown_commands):
            return "shutdown", None, None  
        
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
       # print(f"{INDENT_OUTPUT}[{self.name}] Listening...")

        if not audio_data:
            self.display.update_data(status="LISTENING", text="Esperando entrada por voz...")
            return

        self.display.update_data(status="PROCESSING", text="Analizando señal de voz...")
        raw_text = self.speech_to_text(audio_data)
        
        if not raw_text:
            self.display.update_data(status="LISTENING", text="No se ha detectado texto claro.")
            return
        
        print(f"{INDENT_OUTPUT}[{self.name}] Audio detected: \"{raw_text}\"")
        self.display.update_data(status="PROCESSING", text=raw_text)
        
        # Process audio
        intent, item, quantity = self.parse_intent(raw_text)

        if intent == "unknown":
            # REFACTORITZACIÓ PER A UNA INTERACCIÓ MÉS NATURAL:
            self.display.update_data(
                status="CONFUSED",                          
                title="Procesando Petición",                
                data_dict={
                    "He escuchado": f'"{raw_text}"',        # Mostrem clarament el que ha entès
                    "->": "No sé cómo ayudarte con esto aún"
                }
                footer="Esperando aclaración del usuario..."
            )
            
            # La veu del robot acompanya de manera natural el que es veu a la pantalla
            self.speak("He entendido lo que decias, pero no sé cómo ayudarte con esa petición. ¿Podrías decirmelo de otra forma?")
            print(f"{INDENT_OUTPUT}[{self.name}] Unknown order. Prompting user for clarification.")
            return
        
        elif intent == "add":
            self.display.update_data(status="SUCCESS", title="Elemento Añadido", data_dict={"Acción": "ADD", "Elemento": item, "Cantidad": quantity})
            self.add_data_task(
                Task(
                    type="add_item", 
                    data={
                        "item": item,
                        "quantity": quantity
                    }
                )
            )

            self.speak(f"He añadido {quantity} de {item}.")

            self.publish_event(
                Event(
                    type="item_added",
                    data={
                        "item": item,
                    },
                    origin=self.name
                )
            )
        
        elif intent == "delete":
            self.display.update_data(status="SUCCESS", title="Elemento Eliminado", data_dict={"Acción": "DELETE", "Elemento": item})
            self.add_data_task(
                Task(
                    type="delete_item", 
                    data={
                        "item": item,
                        "quantity": quantity
                    }
                )
            )

            self.speak(f"He borrado el producto {item} completamente de la lista.")

            self.publish_event(
                Event(
                    type="item_deleted",
                    data={
                        "item": item,
                        "quantity": quantity
                    },
                    origin=self.name
                )
            )
        elif intent == "read":
            lista_actual = self.shared_data.get('shopping_list', {})
            datos_pantalla = lista_actual if lista_actual else {"Estado": "Lista vacía"}
            self.display.update_data(status="SUCCESS", title="Lectura de Datos", data_dict=datos_pantalla)
           
            if self.shared_data['shopping_list']:
                formatted_list = ", ".join([f"{qty} {prod}" for prod, qty in self.shared_data['shopping_list'].items()])
                self.speak(f"en la lista tienes: {formatted_list}.")
            else:
                self.speak("la lista de la compra está vacía.")

            self.publish_event(
                Event(
                    type="read_list",
                    data=self.shared_data['shopping_list'],
                    origin=self.name
                )
            )
        elif intent == "clear":
            self.display.update_data(status="SUCCESS", title="Limpieza de Datos", data_dict={"Registros": "Todos eliminados"})
            self.add_data_task(
                Task(type="clear_list")
            )

            self.speak("He vaciado la lista de la compra por completo.")

            self.publish_event(
                Event(
                    type="list_cleared",
                    origin=self.name
                )
            )
            
        # AFEGIR AQUEST BLOC DINS DE LA CADENA IF/ELIF DE PROCESS_AUDIO
        elif intent == "shutdown":
            # 1. Actualitzem el display amb un estat de comiat amable
            self.display.update_data(
                status="SHUTDOWN",
                title="Apagando Sistema",
                data_dict={
                    "Orden": "Cierre solicitado",
                    "Estado": "Guardando datos y saliendo..."
                },
                footer="Desconexión en curso."
            )
            
            # 2. El robot s'acomiada parlant de viva veu
            self.speak("Entendido. Procedo a apagar el sistema. ¡Hasta pronto!")
            
            # 3. Notifiquem al Planner global que volem tancar-ho tot
            self.publish_event(
                Event(
                    type="shutdown_requested",
                    origin=self.name
                )
            )
            print(f"{INDENT_OUTPUT}[{self.name}] Shutdown request published. Exiting loop.")
            return

            
    
    def handle_task(self, task):
        if task.type == "speak":
            # Play audio to talk back
            print(f"{INDENT_OUTPUT}[{self.name}] Playing audio.")
            self.speak(task.data)

    def speak(self, text):
        # el planificador orquesta la comunicacion: pide el audio a hri y se lo pasa a actuacion
        print(f"{INDENT_OUTPUT}[{self.name}] Robot: {text}")
        audio_bytes = self.text_to_speech(text)
        
        if audio_bytes:
            self.speaker.play_audio(audio_bytes)
            # self.shared_data['audio_to_speak'] = audio_bytes

            # self.add_data_task(
            #     Task(
            #         type="audio_to_speak", 
            #         data=audio_bytes
            #     )
            # )

            # self.publish_event(
            #     Event(
            #         type="speak",
            #         origin=self.name
            #     )
            # )

    def loop(self):
        self.process_audio()
        self.display.refresh()


            