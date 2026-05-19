import os
import sys
from dotenv import load_dotenv

# anadimos la raiz del proyecto al path para importar modulos correctamente
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from source.services import storage_service
from source.services import speech_processing
from source.services import audio_sensor
from source.modules.actuation import speaker

# inicializar entorno y credenciales
load_dotenv()
api_key = os.getenv("API_KEY")

if not api_key:
    print("error critico: falta la api_key en el archivo .env")
    exit()

def speak(text):
    # el planificador orquesta la comunicacion: pide el audio a hri y se lo pasa a actuacion
    print(f"robot: {text}")
    audio_bytes = speech_processing.text_to_speech(text, api_key)
    if audio_bytes:
        speaker.play_audio(audio_bytes)

def main_loop():
    # capa 1: toma de decisiones. inicializacion de hardware
    speaker.init_speaker()
    print("sistema iniciado. el planificador esta orquestando las capas.")
    speak("sistema iniciado. dime qué necesitas.")
    
    while True:
        print("\nplanificador: esperando eventos sensoriales...")
        
        # 1. obtener datos del sensor (microfono)
        audio_data = audio_sensor.capture_audio()
        if not audio_data:
            continue

        # 2. enviar datos a hri para stt (speech-to-text)
        raw_text = speech_processing.speech_to_text(audio_data, api_key)
        if not raw_text:
            continue
            
        print(f"hri reporta: '{raw_text}'")
        
        # 3. clasificar la intencion del usuario
        intent, item, quantity = speech_processing.parse_intent(raw_text)
        
        if intent == "unknown":
            print("planificador: orden desconocida. ignorando evento.")
            continue
            
        # 4. logica de negocio interactuando con data_manager y respondiendo
        shopping_list = storage_service.load_list()
        
        if intent == "add":
            if item:
                shopping_list[item] = shopping_list.get(item, 0) + quantity
                storage_service.save_list(shopping_list)
                speak(f"he añadido {quantity} de {item}. ya tienes {shopping_list[item]} en total.")
            else:
                speak("no he entendido qué producto quieres añadir.")
                
        elif intent == "delete":
            if item in shopping_list:
                del shopping_list[item]
                storage_service.save_list(shopping_list)
                speak(f"he borrado el producto {item} completamente de la lista.")
            else:
                speak(f"no encontré {item} en la lista.")
                
        elif intent == "read":
            if shopping_list:
                formatted_list = ", ".join([f"{qty} {prod}" for prod, qty in shopping_list.items()])
                speak(f"en la lista tienes: {formatted_list}.")
            else:
                speak("la lista de la compra está vacía.")
                
        elif intent == "clear":
            storage_service.save_list({})
            speak("he vaciado la lista de la compra por completo.")

if __name__ == "__main__":
    main_loop()