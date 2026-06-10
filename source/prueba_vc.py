# robot_scanner.py
import cv2
import base64
import requests
import time
import os  # 👈 Importamos el módulo de sistema para gestionar carpetas

# URL de tu servidor en Google Cloud Run para el escaneo de estanterías
URL_CLOUD = "https://cart-on-api-225606614592.europe-southwest1.run.app/api/escanear"

def capturar_y_enviar():
    print("📷 Iniciando cámara Sunny (via V4L2 nativo)...")

    # Abre la cámara 0 usando el backend estándar de vídeo de Linux
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    # 🔍 CONFIGURACIÓN DEL SENSOR SUNNY:
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Damos 2 segundos para que el sensor Sunny regule el enfoque y la luz automáticamente
    print("⏳ Esperando estabilización del sensor...")
    time.sleep(2)
    
    # Capturamos la trama física
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("❌ Error: No se pudo capturar la imagen de la cámara Sunny.")
        return

    print("✅ Foto capturada con éxito.")

    # =========================================================================
    # 💾 NUEVA SECCIÓN: GUARDAR IMAGEN LOCALMENTE CON TIMESTAMPS
    # =========================================================================
    carpeta_guardado = "capturas"
    
    # Si la carpeta no existe en el directorio actual, la creamos mágicamente
    if not os.path.exists(carpeta_guardado):
        os.makedirs(carpeta_guardado)
        print(f"📁 Carpeta '{carpeta_guardado}' creada correctamente.")
        
    # Generamos un nombre único basado en el tiempo exacto (AñoMesDia_HoraMinutoSegundo)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    ruta_imagen = os.path.join(carpeta_guardado, f"captura_{timestamp}.jpg")
    
    # Guardamos la matriz del frame como un archivo físico en el disco de la Raspy
    cv2.imwrite(ruta_imagen, frame)
    print(f"💾 Imagen respaldada localmente en: {ruta_imagen}")
    # =========================================================================

    print("📸 Codificando para enviar al Cloud...")
    
    # Codificamos la foto a Base64 para mandarla por HTTP
    _, buffer = cv2.imencode('.jpg', frame)
    imagen_base64 = base64.b64encode(buffer).decode('utf-8')

    # Preparamos el paquete JSON estructurado para tu backend
    payload = {
        "imagen_base64": imagen_base64
    }

    print("🚀 Enviando foto al servidor Cloud...")
    try:
        respuesta = requests.post(URL_CLOUD, json=payload, timeout=15)
        
        if respuesta.status_code == 200:
            datos_respuesta = respuesta.json()
            print("✅ Respuesta del servidor:", datos_respuesta)
        else:
            print(f"❌ Error en el servidor: {respuesta.status_code}")
            print(respuesta.text)
            
    except Exception as e:
        print(f"❌ Error de conexión con Cloud Run: {e}")

if __name__ == "__main__":
    print("--- MODO ESCANEO CART-ON ---")
    input("Pulsa ENTER para escanear la estantería...")
    capturar_y_enviar()