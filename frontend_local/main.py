import cv2
import requests
import time

print("🤖 Iniciando sistema sensorial de Cart-ON...")

# ⚠️ CAMBIA ESTO: Pon aquí la URL pública que te dio Google Cloud Run 
# (Recuerda añadir el /api/v1/ask al final)
URL_NUBE = "http://localhost:8080/api/v1/ask"

def capturar_y_enviar():
    # 1. Encender la cámara
    cap = cv2.VideoCapture(0)
    
    # Damos 2 segundos para que la cámara enfoque bien el supermercado
    print("📷 Calentando cámara...")
    time.sleep(2) 
    
    # 2. Leer un frame (hacer la foto)
    exito, frame = cap.read()
    cap.release() # Apagamos la cámara enseguida para no gastar recursos

    if not exito:
        print("❌ Error: No se pudo leer la cámara.")
        return

    print("✅ Foto capturada. Empaquetando datos...")

    # 3. Convertir la imagen de OpenCV a un formato que se pueda enviar por internet (Bytes)
    _, img_codificada = cv2.imencode('.jpg', frame)
    imagen_bytes = img_codificada.tobytes()

    # 4. Preparar el paquete (Payload)
    # Por ahora enviamos la foto y un texto de prueba simulando el micrófono
    archivos = {
        'image_file': ('foto_supermercado.jpg', imagen_bytes, 'image/jpeg')
    }
    datos = {
        'texto_debug': '¿Cuánto cuesta este producto?'
    }

    # 5. Enviar el paquete a Google Cloud Run
    print("🚀 Enviando paquete a la nube...")
    try:
        # El robot se queda esperando a que el servidor piense
        respuesta = requests.post(URL_NUBE, files=archivos, data=datos)
        
        # 6. Leer y mostrar la respuesta que nos manda el servidor
        if respuesta.status_code == 200:
            json_respuesta = respuesta.json()
            print("\n" + "="*50)
            print("☁️ RESPUESTA DEL SERVIDOR CLOUD:")
            print(f"Mensaje: {json_respuesta.get('texto', 'Sin texto')}")
            print("="*50 + "\n")
        else:
            print(f"⚠️ El servidor devolvió un error: {respuesta.status_code}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

# Ejecutamos la función
capturar_y_enviar()