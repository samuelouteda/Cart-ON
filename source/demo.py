import os
import time
import sys

# 🚀 TRUCO DEFINITIVO NÚMERO 2: Radar de carpetas ampliado
directorio_actual = os.path.dirname(os.path.abspath(__file__)) # Carpeta 'source'
directorio_padre = os.path.dirname(directorio_actual) # Carpeta 'Cart-ON'
directorio_backend = os.path.join(directorio_padre, "backend_cloud") # Carpeta 'backend_cloud'

# Añadimos todas al radar de Python
sys.path.append(directorio_padre)
sys.path.append(directorio_backend) # <- ¡ESTO ARREGLA EL ERROR DE AI_SERVICES!
sys.path.append(directorio_actual)

import base64
import requests
import qrcode
import cv2
import numpy as np
import pygame
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Importamos tu orquestador
from backend_cloud.orchestrator.cloud_planner import PlannerCloud

# ==========================================
# 🔧 CONFIGURACIÓN Y CLAVES API
# ==========================================
load_dotenv() # Carga las variables de tu archivo .env

# Intenta coger las claves del .env. Si no las encuentra, ponlas aquí temporalmente entre las comillas:
GOOGLE_API_KEY = os.getenv("AIzaSyCMV4L39MGvadx6XLsm_99Comj4sZ5EUn4", "AIzaSyCMV4L39MGvadx6XLsm_99Comj4sZ5EUn4") 

# ==========================================
# 🎬 FUNCIONES MULTIMEDIA INCORPORADAS
# ==========================================
def text_to_speech(text_to_say, api_key):
    """Genera los bytes de audio acelerados un 15%."""
    endpoint_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    payload = {
        "input": {"text": text_to_say},
        "voice": {"languageCode": "es-ES", "name": "es-ES-Neural2-F"},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.15}
    }
    try:
        response = requests.post(endpoint_url, json=payload)
        response_json = response.json()
        if "audioContent" in response_json:
            return base64.b64decode(response_json["audioContent"])
    except Exception as e:
        print(f"🔴 Error TTS: {e}")
    return None

def reproducir_audio(audio_bytes):
    """Reproduce los bytes de MP3 bloqueando la ejecución hasta que termine de hablar."""
    if not audio_bytes:
        return
    
    # Guardamos en un archivo temporal seguro
    temp_file = "temp_carton_voice.mp3"
    with open(temp_file, "wb") as f:
        f.write(audio_bytes)
        
    pygame.mixer.init()
    pygame.mixer.music.load(temp_file)
    pygame.mixer.music.play()
    
    # Esperamos a que termine de hablar
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
        
    pygame.mixer.quit()
    os.remove(temp_file) # Limpiamos la basura

def mostrar_pantalla_mapa(lat, lng, aula, api_key):
    """Descarga el mapa, genera el QR, los fusiona y los muestra por pantalla con OpenCV."""
    try:
        # 1. Descargar mapa estático
        url_mapa = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lng}&zoom=19&size=720x400&maptype=roadmap&markers=color:red%7C{lat},{lng}&key={api_key}"
        resp = requests.get(url_mapa)
        if resp.status_code != 200:
            print("🔴 Error descargando el mapa. Revisa la API KEY o las restricciones de IP.")
            return
        mapa_img = Image.open(BytesIO(resp.content)).convert("RGB")

        # 2. Generar QR interactivo
        url_navegacion = f"https://maps.google.com/?q={lat},{lng}"
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url_navegacion)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # 3. Fusionar (Pegar el QR en la esquina inferior derecha)
        margen = 15
        pos_x = mapa_img.width - qr_img.width - margen
        pos_y = mapa_img.height - qr_img.height - margen
        mapa_img.paste(qr_img, (pos_x, pos_y))

        # 4. Transformar para OpenCV y añadir título
        open_cv_image = np.array(mapa_img)
        open_cv_image = open_cv_image[:, :, ::-1].copy() # Convertir de RGB a BGR (formato OpenCV)
        
        cv2.putText(open_cv_image, f"Cart-ON GPS -> Destino: {aula}", (15, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # 5. Mostrar ventana multimedia
        cv2.imshow("Cart-ON Multimedia Display", open_cv_image)
        print("\n👉 [El mapa está en pantalla]. Escanea el QR con tu móvil para probarlo.")
        print("🛑 Pulsa CUALQUIER TECLA (con la imagen seleccionada) para cerrarla y continuar.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"🔴 Error mostrando el mapa: {e}")

# ==========================================
# 🚀 EJECUCIÓN PRINCIPAL DE LA DEMO
# ==========================================
def ejecutar_demo():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("==================================================")
    print(" 🎬 INICIANDO MODO DEMOSTRACIÓN (100% CONTROLADO) 🎬")
    print("==================================================\n")
    
    print("⚙️ Cargando el Orquestador en la Nube y conectando a MySQL...")
    planner = PlannerCloud()
    time.sleep(1)

    # 1. Definimos el guion de la presentación
    pasos_demo = [
        {
            "titulo": "PASO 1: Rechazo de Modos Inexistentes (Robustez Lógica)",
            "explicacion": "Vamos a pedirle un modo que no existe para demostrar que la IA rechaza inventar datos.",
            "texto_simulado": "Cart-ON, cambia al modo ninja."
        },
        {
            "titulo": "PASO 2: Cambio de Contexto (Modo Escuela)",
            "explicacion": "Cambiamos al entorno universitario... La IA reconoce el cambio de contexto y se adapta a ser un asistente académico en lugar de un ayudante de compras.",
            "texto_simulado": "Cambia al modo escuela, por favor."
        },
        {
            "titulo": "PASO 3: Búsqueda Segura (Robustez SQL)",
            "explicacion": "Le pedimos una clase inventada. La IA extrae la info, pero al buscar en BBDD dice que no existe.",
            "texto_simulado": "¿Dónde está el aula de magia negra?"
        },
        {
            "titulo": "PASO 4: Procesamiento Complejo y Multimodal (SQL + Google Maps + TTS)",
            "explicacion": "Pedimos la asignatura 'visión por computador' en español. Qwen la traduce al catalán, MySQL saca las coordenadas GPS, y Python genera voz, mapa interactivo y código QR.",
            "texto_simulado": "¿Dónde es la clase de visión por computador del grupo 441?"
        }
    ]

    # 2. Bucle secuencial controlado
    for paso in pasos_demo:
        print("\n" + "="*60)
        print(f"🚀 {paso['titulo']}")
        print(f"🗣️  Info: {paso['explicacion']}")
        print("="*60)
        
        # Pausa hasta que estés listo para enseñarlo
        input("\n👉 Pulsa ENTER cuando quieras procesar este paso...")
        
        print(f"\n[Micrófono Simulado] 🎤 Escuchado: '{paso['texto_simulado']}'")
        print("⏳ Analizando intención, conectando a BD y generando respuesta...")
        
        inicio_tiempo = time.time()
        
        # Procesamos la lógica central (LLM + SQL)
        respuesta = planner.procesar_peticion_hri(paso['texto_simulado'], imagen_bytes=None)
        
        tiempo_total = round(time.time() - inicio_tiempo, 2)
        print(f"✅ Respuesta lógica generada en {tiempo_total} segundos.")
        print(f"🤖 [Cart-ON Dice]: {respuesta['texto']}")
        
        # Generamos y reproducimos la voz
        print("🔊 Sintetizando audio (Google TTS)...")
        audio_bytes = text_to_speech(respuesta['texto'], GOOGLE_API_KEY)
        reproducir_audio(audio_bytes)
        
        # Si la respuesta incluye coordenadas, activamos el mapa
        if respuesta.get('lat') and respuesta.get('lng'):
            print(f"🗺️  Coordenadas detectadas: Lat: {respuesta['lat']}, Lng: {respuesta['lng']}")
            mostrar_pantalla_mapa(respuesta['lat'], respuesta['lng'], respuesta['aula'], GOOGLE_API_KEY)
            
    print("\n🎉 DEMOSTRACIÓN FINALIZADA. ¡Sistemas Multimedia superado con éxito!")

if __name__ == "__main__":
    if GOOGLE_API_KEY == "TU_API_KEY_AQUI":
        print("⚠️ ALERTA: No has configurado tu GOOGLE_API_KEY. Edita el archivo demo_perfecta.py antes de lanzarlo.")
    else:
        ejecutar_demo()