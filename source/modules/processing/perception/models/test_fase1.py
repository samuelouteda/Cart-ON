import sys
import os

# Ajuste de rutas por si lo ejecutas desde una subcarpeta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

import cv2
import time
from ultralytics import YOLO

print("📸 Iniciando Fase 1: Escáner de Recolección Cart-ON...")

# 1. Configuración de Rutas y Modelo
# Asegúrate de poner el nombre exacto de tu modelo de estanterías aquí
MODELO_SHELF_PATH = 'source/modules/processing/perception/models/yolov8s_shelf.pt'
CARPETA_GUARDADO = 'source/data/recortes_pendientes/'

# Creamos la carpeta si no existe
if not os.path.exists(CARPETA_GUARDADO):
    os.makedirs(CARPETA_GUARDADO)
    print(f"📁 Carpeta creada: {CARPETA_GUARDADO}")

try:
    modelo_escaner = YOLO(MODELO_SHELF_PATH)
except Exception as e:
    print(f"❌ Error al cargar el modelo: {e}. ¿Seguro que el archivo {MODELO_SHELF_PATH} está en esta carpeta?")
    sys.exit()

# 2. Configuración de la Cámara y Temporizador
cap = cv2.VideoCapture(0)
contador_fotos = 0
tiempo_ultima_foto = 0
COOLDOWN_FOTOS = 1.0  # Guarda una foto cada 1 segundo como máximo para no saturar

print("🚀 Sistema listo. Pasa los productos por delante de la cámara...")

while cap.isOpened():
    exito, frame = cap.read()
    if not exito:
        print("❌ Error al leer la cámara.")
        break

    # Guardamos una copia limpia del frame original ANTES de que YOLO pinte recuadros
    # Esto es crucial: queremos que la IA de la Fase 2 vea la foto limpia, no un recuadro verde.
    frame_limpio = frame.copy()

    # YOLO analiza buscando bultos
    resultados = modelo_escaner(frame, stream=True, verbose=False)

    tiempo_actual = time.time()

    for r in resultados:
        cajas = r.boxes
        for caja in cajas:
            confianza = caja.conf[0].item()
            
            # Si ve un bulto con más de 50% de seguridad
            if confianza > 0.50:
                # Sacamos las coordenadas del recuadro
                x1, y1, x2, y2 = map(int, caja.xyxy[0])
                
                # Dibujamos en pantalla para que TÚ sepas que lo ha visto
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, "Detectando caja...", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                # ¿Ha pasado suficiente tiempo desde la última foto?
                if (tiempo_actual - tiempo_ultima_foto) > COOLDOWN_FOTOS:
                    
                    # MAGIA DE OPENCV: Recortamos el trozo de la foto original (limpia)
                    # Ojo: OpenCV usa el formato imagen[y_inicio:y_fin, x_inicio:x_fin]
                    recorte = frame_limpio[y1:y2, x1:x2]
                    
                    # Verificamos que el recorte no esté vacío (a veces YOLO falla cerca del borde)
                    if recorte.size > 0:
                        contador_fotos += 1
                        nombre_archivo = f"{CARPETA_GUARDADO}crop_{contador_fotos:04d}.jpg"

                        # Pasamos el recorte a blanco y negro
                        gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)

                        # Calculamos el nivel de enfoque (mientras más alto, más nítida)
                        nivel_enfoque = cv2.Laplacian(gris, cv2.CV_64F).var()

                        # Solo guardamos si supera el umbral de nitidez (ej: 100)
                        if nivel_enfoque > 100:
                            cv2.imwrite(nombre_archivo, recorte)
                            print(f"✅ Recorte NÍTIDO guardado. (Score: {nivel_enfoque:.0f})")
                        else:
                            print(f"⚠️ Descartado por borroso. (Score: {nivel_enfoque:.0f})")
                        
                        tiempo_ultima_foto = tiempo_actual

    # Mostramos lo que ve la cámara (con los recuadros dibujados)
    cv2.imshow('Fase 1: Escaner Cart-ON', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"🛑 Fin de la recolección. Se han guardado {contador_fotos} recortes en '{CARPETA_GUARDADO}'.")