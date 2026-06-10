# robot_scanner.py
import cv2
import base64
import requests
import time

# URL de tu servidor FastAPI (cámbiala por la de tu Cloud Run o tu IP local para pruebas)
URL_CLOUD = "http://127.0.0.1:8000/api/escanear"

def capturar_y_enviar():
    print("📷 Iniciando cámara...")
    # Abre la cámara web (0 es la cámara por defecto)
    cap = cv2.VideoCapture(0)
    
    # Damos un segundo para que la cámara enfoque bien
    time.sleep(1)
    
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("❌ Error: No se pudo capturar la imagen de la cámara.")
        return

    print("✅ Foto capturada. Codificando para enviar...")
    
    # Codificamos la foto a Base64 para mandarla por HTTP
    _, buffer = cv2.imencode('.jpg', frame)
    imagen_base64 = base64.b64encode(buffer).decode('utf-8')

    # Preparamos el paquete JSON
    payload = {
        "imagen_base64": imagen_base64
    }

    print("🚀 Enviando foto al servidor Cloud...")
    try:
        respuesta = requests.post(URL_CLOUD, json=payload)
        
        if respuesta.status_code == 200:
            datos_respuesta = respuesta.json()
            print("✅ Respuesta del servidor:", datos_respuesta)
        else:
            print(f"❌ Error en el servidor: {respuesta.status_code}")
            print(respuesta.text)
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    print("--- MODO ESCANEO CART-ON ---")
    input("Pulsa ENTER para escanear la estantería...")
    capturar_y_enviar()