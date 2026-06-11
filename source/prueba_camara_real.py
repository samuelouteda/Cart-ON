import cv2
import requests
import subprocess
import time
import numpy as np
import base64

# ⚠️ CORREGIT: Apuntem directament a la teva aplicació d'IA, no al gateway de rutes
URL_CLOUD = "https://cart-on-api-225606614592.europe-southwest1.run.app/api/escanear"

def capturar_desde_hardware_disponible() -> bytes:
    print("🔍 [Cámara] Detectando hardware de captura...")
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
    except:
        print("⚠️ El sensor nativo falló, intentando OpenCV...")
        
    try:
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
                return buffer.tobytes()
    except Exception as e:
        print(f"⚠️ OpenCV falló: {e}")
        
    raise RuntimeError("No se detectó ninguna cámara funcional.")

if __name__ == "__main__":
    print("🤖 --- MODO CLIENTE LIGERO CART-ON ---")
    
    try:
        # 1. Capturem la foto del hardware real
        bytes_foto = capturar_desde_hardware_disponible()
        
        # 2. Convertim a Base64 perquè el teu Payload del núvol demana {"imagen_base64": "..."}
        print("🔄 Codificando imagen a Base64...")
        imagen_local_b64 = base64.b64encode(bytes_foto).decode('utf-8')
        
        # 3. Enviem com a JSON normal (com ho demana el teu codi de FastAPI)
        print(f"🚀 Enviando JSON al servidor de IA en Cloud Run...")
        payload = {"imagen_base64": imagen_local_b64}
        respuesta = requests.post(URL_CLOUD, json=payload, timeout=45)
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            print(f"☁️ ¡Respuesta recibida con éxito de la IA!")
            
            # Mostrem el text del que ha trobat l'optimizador visual de la UAB
            if "detectado" in datos:
                print(f"📦 Detecciones reales: {datos['detectado']}")
            
            # 🛠️ Recuperem el camp 'imagen_anotada' que el teu codi SI que genera
            clave_imagen = "imagen_anotada" 
            
            if clave_imagen in datos and datos[clave_imagen]:
                print("🔄 Descodificando 'imagen_anotada' a imagen real...")
                img_data_repuesta = datos[clave_imagen]
                
                if "," in img_data_repuesta:
                    img_data_repuesta = img_data_repuesta.split(",")[1]
                
                img_bytes_respuesta = base64.b64decode(img_data_repuesta)
                np_arr = np.frombuffer(img_bytes_respuesta, np.uint8)
                img_final = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                print("🖼️ ¡Mostrando imagen procesada! Presiona cualquier tecla sobre la ventana para cerrarla.")
                cv2.imshow("Cart-ON - Resultado Cloud Run", img_final)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            else:
                print("⚠️ No se encontró 'imagen_anotada' en el JSON.")
                print(f"Campos devueltos por tu IA: {list(datos.keys())}")
        else:
            print(f"❌ Fallo en el servidor de IA: {respuesta.status_code} - {respuesta.text}")
            
    except Exception as e:
        print(f"❌ Error crítico: {e}")