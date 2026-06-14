import base64
import requests
import time
import numpy as np
import cv2
import os

# ⚠️ LA URL REAL DE TU NUBE
CLOUD_URL = "https://cart-on-api-225606614592.europe-west1.run.app/api/v1/escaneo_inventario"

def test_pipeline_vision(ruta_imagen):
    print(f"🤖 [TEST] Iniciando simulador de visión con archivo: {ruta_imagen}")
    
    if not os.path.exists(ruta_imagen):
        print(f"🔴 Error: El archivo '{ruta_imagen}' no existe.")
        return

    frame = cv2.imread(ruta_imagen)
    if frame is None:
        print("🔴 Error: No se pudo abrir la imagen.")
        return

    # Codificamos a Base64
    _, buffer = cv2.imencode('.jpg', frame)
    b64_image = base64.b64encode(buffer).decode('utf-8')

    payload = {
        "imagen_base64": b64_image,
        "robot_x": 5.42, 
        "robot_y": 1.15  
    }

    print("☁️ Enviando petición a la Nube...")
    try:
        res = requests.post(CLOUD_URL, json=payload, timeout=30)
        res.raise_for_status()
        
        datos = res.json()
        print(f"🛒 Productos detectados: {datos.get('detectado')}")

        if "imagen_anotada" in datos and datos["imagen_anotada"]:
            # 1. Decodificamos y convertimos a imagen
            img_bytes = base64.b64decode(datos["imagen_anotada"])
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img_final = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # 2. GUARDAR EN DISCO
            nombre_archivo_salida = "resultado_inventario.jpg"
            cv2.imwrite(nombre_archivo_salida, img_final)
            print(f"💾 Imagen guardada exitosamente como: {nombre_archivo_salida}")

            # 3. Mostrarla
            cv2.imshow("Cart-ON Vision Test", img_final)
            print("\n👀 Pulsa cualquier tecla para cerrar.")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("⚠️ El servidor no devolvió una imagen anotada.")

    except Exception as e:
        print(f"🔴 Error de conexión: {e}")

if __name__ == "__main__":
    archivo = input("Introduce la ruta de la imagen: ").strip().replace('"', '')
    test_pipeline_vision(archivo)