import sys
import os
import cv2
from ultralytics import YOLO

# Ajuste de rutas por si lo ejecutas desde una subcarpeta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

print("📸 Iniciando Fase 1: Escáner de Recolección (MODO FOTO)...")

# ==========================================
# 1. Configuración de Rutas y Modelo
# ==========================================
MODELO_SHELF_PATH = 'source/modules/processing/perception/models/yolov8s_shelf.pt'
CARPETA_GUARDADO = 'source/data/recortes_pendientes/'

# ⚠️ PON AQUÍ LA RUTA DE LA FOTO QUE QUIERAS PROBAR
IMAGEN_PRUEBA = 'C:\\Users\\User\\Documents\\GitHub\\Cart-ON\\a.jpeg' 

# Creamos la carpeta si no existe
if not os.path.exists(CARPETA_GUARDADO):
    os.makedirs(CARPETA_GUARDADO)
    print(f"📁 Carpeta creada: {CARPETA_GUARDADO}")

try:
    modelo_escaner = YOLO(MODELO_SHELF_PATH)
except Exception as e:
    print(f"❌ Error al cargar el modelo: {e}")
    sys.exit()

# ==========================================
# 2. Lectura y Análisis de la Imagen
# ==========================================
frame = cv2.imread(IMAGEN_PRUEBA)

if frame is None:
    print(f"❌ Error: No se ha podido leer la imagen en la ruta: '{IMAGEN_PRUEBA}'")
    print("Asegúrate de que la foto existe y la ruta está bien escrita.")
    sys.exit()

print(f"🚀 Analizando la imagen '{IMAGEN_PRUEBA}'...")

# Guardamos una copia limpia para recortar
frame_limpio = frame.copy()

# YOLO analiza la foto (quitamos stream=True porque es solo una imagen)
resultados = modelo_escaner(frame, verbose=False)

contador_fotos = 0

for r in resultados:
    cajas = r.boxes
    for caja in cajas:
        confianza = caja.conf[0].item()
        
        # Si ve un bulto con más de 50% de seguridad
        if confianza > 0.20:
            x1, y1, x2, y2 = map(int, caja.xyxy[0])
            
            # Dibujamos el recuadro en la imagen de visualización
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
            cv2.putText(frame, f"Caja {confianza:.2f}", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

            # Recortamos la imagen limpia
            recorte = frame_limpio[y1:y2, x1:x2]
            
            if recorte.size > 0:
                contador_fotos += 1
                nombre_archivo = f"{CARPETA_GUARDADO}crop_estatico_{contador_fotos:04d}.jpg"

                # Comprobación de borrosidad (Laplaciano)
                gris = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
                nivel_enfoque = cv2.Laplacian(gris, cv2.CV_64F).var()

                # Umbral de nitidez (bajamos un poco a 80 para fotos estáticas que puedan tener peor luz)
                if nivel_enfoque > 80:
                    cv2.imwrite(nombre_archivo, recorte)
                    print(f"✅ Recorte {contador_fotos} NÍTIDO guardado. (Score: {nivel_enfoque:.0f})")
                else:
                    print(f"⚠️ Recorte {contador_fotos} Descartado por borroso. (Score: {nivel_enfoque:.0f})")

# ==========================================
# 3. Resultado Visual
# ==========================================
print("-" * 50)
print(f"🛑 Análisis completado. Se han guardado {contador_fotos} recortes en '{CARPETA_GUARDADO}'.")
print("👀 Mostrando resultado... Pulsa CUALQUIER TECLA para cerrar la ventana.")

# Mostramos la imagen final con los recuadros pintados
cv2.imshow('Fase 1: Resultado Modo Foto', frame)

# El script se pausa aquí hasta que pulses una tecla teniendo la ventana de la imagen seleccionada
cv2.waitKey(0)
cv2.destroyAllWindows()