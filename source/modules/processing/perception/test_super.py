import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

import cv2
import time
import threading  # <--- LA LIBRERÍA MÁGICA PARA QUITAR EL LAG
from ultralytics import YOLO
from source.modules.processing.HRI.HRI_manager import SupermercadoHRI

print("🤖 Iniciando sistema visual SIN LAG (Multihilo)...")

db_config = {
    'host': '34.28.135.54',
    'user': 'marco-mejias',
    'password': 'cart-on-Fortnite67',
    'database': 'carton_db'
}

hri_super = SupermercadoHRI(db_config)
modelo_vision = YOLO('yolov8s.pt') 

CLASES_PERMITIDAS = [39, 46, 47, 73] # Ajusta estos IDs a tus productos

# =========================================================================
# 🧵 FUNCION EN SEGUNDO PLANO (El trabajador que va a por el precio)
# =========================================================================
def consultar_precio_en_segundo_plano(nombre_producto):
    respuesta_robot = hri_super.procesar_peticion(nombre_producto)
    print(f"\n👀 Veo claramente: {nombre_producto}")
    print(f"💬 Cart-ON dice: {respuesta_robot}")

# =========================================================================

cap = cv2.VideoCapture(0)

ultimo_producto_visto = ""
tiempo_ultima_consulta = 0
COOLDOWN_SEGUNDOS = 3

while cap.isOpened():
    exito, frame = cap.read()
    if not exito: break

    # YOLO analiza la imagen (esto es súper rápido, no da lag)
    resultados = modelo_vision(frame, stream=True, verbose=False, classes=CLASES_PERMITIDAS)

    for r in resultados:
        cajas = r.boxes
        for caja in cajas:
            confianza = caja.conf[0].item()
            if confianza > 0.60:
                clase_id = int(caja.cls[0].item())
                nombre_yolo = modelo_vision.names[clase_id]

                # Dibujamos en pantalla al instante
                x1, y1, x2, y2 = map(int, caja.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(frame, f"{nombre_yolo} {confianza:.2f}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                tiempo_actual = time.time()
                if nombre_yolo != ultimo_producto_visto or (tiempo_actual - tiempo_ultima_consulta) > COOLDOWN_SEGUNDOS:
                    
                    # 🚀 ¡AQUÍ ESTÁ EL CAMBIO!
                    # Lanzamos la consulta a la BD en un hilo separado para NO parar el vídeo
                    hilo = threading.Thread(target=consultar_precio_en_segundo_plano, args=(nombre_yolo,))
                    hilo.start()
                    
                    ultimo_producto_visto = nombre_yolo
                    tiempo_ultima_consulta = tiempo_actual

    cv2.imshow('Ojos de Cart-ON', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()