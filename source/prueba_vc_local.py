import cv2
import base64
import requests
import time
import numpy as np
import os

URL = "http://127.0.0.1:8000/api/test-scan"

def get_image_base64():
    cap = cv2.VideoCapture(0)
    time.sleep(1)
    ret, frame = cap.read()
    cap.release()

    if ret:
        print("✅ Foto capturada con éxito.")
        _, buffer = cv2.imencode('.jpg', frame)
        return base64.b64encode(buffer).decode('utf-8')
    else:
        print("⚠️ No hay cámara. Intentando 'foto.jpg'...")
        if os.path.exists("foto.jpg"):
            with open("foto.jpg", "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        return None

if __name__ == "__main__":
    print("📸 Iniciando escaneo...")
    b64 = get_image_base64()
    
    if b64:
        print("🚀 Enviando al servidor...")
        try:
            res = requests.post(URL, json={"imagen_base64": b64})
            datos = res.json()
            
            if "imagen_anotada" in datos:
                print(f"☁️ Respuesta OK: {datos['detectado']}")
                
                # Descomprimimos la foto pintada que nos mandó el Cloud
                img_bytes = base64.b64decode(datos["imagen_anotada"])
                np_arr = np.frombuffer(img_bytes, np.uint8)
                img_final = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                # Mostramos la ventana (Pulsa cualquier tecla para cerrarla)
                print("👀 Mostrando resultado... (Pulsa cualquier tecla en la ventana para salir)")
                cv2.imshow("Vision Cart-ON (Cloud Processed)", img_final)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                
            else:
                print(f"❌ Fallo: {datos}")
                
        except Exception as e:
            print(f"❌ Error de conexión: {e}")