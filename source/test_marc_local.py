import cv2
import base64
import requests
import subprocess
import time
import numpy as np

# ⚠️ Cambia esta URL por la IP de tu servidor Cloud Run cuando lo despliegues
URL_CLOUD = "http://127.0.0.1:8000/api/escanear"

# ==========================================
# 🛠️ FUNCIÓN DE DETECCIÓN Y CAPTURA AUTOMÁTICA DE HARDWARE
# ==========================================
def capturar_desde_hardware_disponible() -> bytes:
    """
    Intenta capturar una imagen usando el hardware disponible en la Raspberry Pi.
    Prueba primero con rpicam-still (sensor nativo) y si falla, recurre a OpenCV V4L2.
    Devuelve los bytes en bruto de la imagen JPEG.
    """
    print("🔍 [Cámara] Detectando hardware de captura...")
    
    # --- MÈTODE 1: Sensor Nativo / Sunny via rpicam-still ---
    try:
        print("📸 Intentando captura con rpicam-still...")
        comanda = [
            "rpicam-still", "-o", "-", 
            "--immediate", "--width", "1280", "--height", "720"
        ]
        resultat = subprocess.run(comanda, check=True, capture_output=True, timeout=10)
        
        if resultat.stdout:
            print("✅ Captura exitosa con rpicam-still.")
            return resultat.stdout
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️ El sensor nativo (rpicam-still) no respondió o no está disponible.")

    # --- MÈTODE 2: Alternativa OpenCV genérica (V4L2 / USB / Webcams) ---
    try:
        print("📹 Intentando captura genérica mediante OpenCV (V4L2)...")
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            time.sleep(1.5)
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                _, buffer = cv2.imencode('.jpg', frame)
                print("✅ Captura exitosa con OpenCV backend V4L2.")
                return buffer.tobytes()
        else:
            cap.release()
            
    except Exception as e:
        print(f"⚠️ El método alternativo de OpenCV también falló: {e}")

    raise RuntimeError("No se detectó ninguna cámara funcional en los puertos del sistema.")

# ==========================================
# FLUJO PRINCIPAL (THIN EDGE)
# ==========================================
if __name__ == "__main__":
    print("🤖 --- MODO CLIENTE LIGERO CART-ON ---")
    
    try:
        # 1. Obtenemos los bytes de la foto desde el hardware físico
        bytes_foto = capturar_desde_hardware_disponible()
        
        # 2. Convertimos a Base64 para poder mandarlo por JSON
        imagen_local_b64 = base64.b64encode(bytes_foto).decode('utf-8')
        
        # 3. Enviamos el paquete al cerebro en la Nube
        print(f"🚀 Enviando paquete al servidor Cloud: {URL_CLOUD}")
        respuesta = requests.post(URL_CLOUD, json={"imagen_base64": imagen_local_b64})
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            print(f"☁️ Respuesta OK: {datos.get('detectado', [])}")
            
            # 4. Mostrar la imagen pintada (Bounding Boxes) que nos devuelve la nube
            if "imagen_anotada" in datos:
                img_bytes_respuesta = base64.b64decode(datos["imagen_anotada"])
                np_arr = np.frombuffer(img_bytes_respuesta, np.uint8)
                img_final = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                print("👀 Mostrando resultado... (Pulsa cualquier tecla en la ventana para salir)")
                cv2.imshow("Vision Cart-ON (Cloud Processed)", img_final)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
        else:
            print(f"❌ Fallo en el servidor: {respuesta.status_code} - {respuesta.text}")
            
    except RuntimeError as e:
        print(f"🔴 Error de hardware en el sistema: {e}")
    except Exception as e:
        print(f"❌ Error crítico en el cliente local: {e}")