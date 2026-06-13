import cv2
import base64
import requests
import time
import numpy as np

# ⚠️ LA URL REAL DE TU NUBE (Asegúrate de que está desplegada)
CLOUD_URL = "https://cart-on-api-225606614592.europe-west1.run.app/api/v1/escaneo_inventario"

def test_pipeline_vision():
    print("🤖 [TEST] Iniciando simulador de visión de Cart-ON...")
    
    # 1. Encendemos la webcam de tu ordenador (0 suele ser la cámara por defecto)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("🔴 Error: No se pudo abrir la webcam de tu PC.")
        return

    print("📸 Preparando cámara... (Tienes 3 segundos para enfocar un objeto)")
    time.sleep(3) # Damos tiempo a que la cámara ajuste el brillo/enfoque
    
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("🔴 Error: No se pudo capturar la foto.")
        return

    print("✅ Foto capturada. Convirtiendo a formato espacial...")

    # 2. Codificamos a Base64
    _, buffer = cv2.imencode('.jpg', frame)
    b64_image = base64.b64encode(buffer).decode('utf-8')

    # 3. Simulamos las coordenadas falsas de donde estaría el robot
    payload = {
        "imagen_base64": b64_image,
        "robot_x": 5.42,  # Coordenada X inventada para el test
        "robot_y": 1.15   # Coordenada Y inventada para el test
    }

    print("☁️ Enviando petición a la Nube (Google Cloud + Qwen)...")
    start_time = time.time()
    
    try:
        # 4. Hacemos la llamada HTTP a tu backend real
        res = requests.post(CLOUD_URL, json=payload, timeout=30)
        res.raise_for_status() # Lanza error si la nube devuelve un 500
        
        datos = res.json()
        end_time = time.time()
        
        print(f"⏱️ ¡Respuesta recibida en {end_time - start_time:.2f} segundos!")
        print(f"🛒 Productos detectados por la IA: {datos.get('detectado')}")

        # 5. Descomprimimos la imagen pintada que nos devuelve el servidor
        if "imagen_anotada" in datos and datos["imagen_anotada"]:
            img_bytes = base64.b64decode(datos["imagen_anotada"])
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img_final = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            print("\n👀 Abriendo ventana con el resultado. (Pulsa cualquier tecla para cerrar)")
            cv2.imshow("Cart-ON Vision Test (Nube Real)", img_final)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
            print("\n🗄️ COMPROBACIÓN FINAL: Abre tu base de datos MySQL.")
            print("Deberías ver los productos insertados con pos_x=5.42 y pos_y=1.15")
        else:
            print("⚠️ El servidor no devolvió una imagen anotada.")

    except Exception as e:
        print(f"🔴 Error de conexión con la nube: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Detalle del servidor: {e.response.text}")

if __name__ == "__main__":
    test_pipeline_vision()