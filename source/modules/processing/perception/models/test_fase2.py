import sys
import os
import shutil
import cv2
from ultralytics import YOLO

# Forzamos la ruta raíz (5 niveles arriba)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))
from source.modules.processing.HRI.HRI_manager import SupermercadoHRI

print("🧠 Iniciando Fase 2 Local: Análisis con YOLO Base...")

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS Y BD
# ==========================================
carpeta_actual = os.path.dirname(os.path.abspath(__file__))
CARPETA_PENDIENTES = os.path.abspath(os.path.join(carpeta_actual, '../../../../../source/data/recortes_pendientes/'))
CARPETA_PROCESADOS = os.path.abspath(os.path.join(carpeta_actual, '../../../../../source/data/procesados/'))

if not os.path.exists(CARPETA_PROCESADOS):
    os.makedirs(CARPETA_PROCESADOS)

db_config = {
    'host': '34.28.135.54',
    'user': 'marco-mejias',
    'password': 'cart-on-Fortnite67',
    'database': 'carton_db'
}

hri_super = SupermercadoHRI(db_config)

# ==========================================
# 2. CARGAMOS LA IA LOCAL (Cero Internet)
# ==========================================
print("⏳ Cargando modelo YOLO base en memoria...")
# YOLO descargará este archivo pequeñito la primera vez si no lo tienes
modelo_vision = YOLO('yolov8s.pt') 

# Clases COCO que tu base de datos entiende: 39=bottle, 46=banana, 47=apple, 73=book
CLASES_PERMITIDAS = [39, 46, 47, 73] 

# ==========================================
# 3. PROCESAMIENTO DE LAS FOTOS
# ==========================================
archivos_pendientes = [f for f in os.listdir(CARPETA_PENDIENTES) if f.endswith('.jpg') or f.endswith('.png')]

if not archivos_pendientes:
    print("✅ No hay recortes pendientes para analizar. El pasillo está procesado.")
    sys.exit()

print(f"📦 Se han encontrado {len(archivos_pendientes)} fotos pendientes. Iniciando escaneo local...")
print("-" * 50)

for archivo in archivos_pendientes:
    ruta_completa = os.path.join(CARPETA_PENDIENTES, archivo)
    
    # Leemos la imagen con OpenCV
    imagen = cv2.imread(ruta_completa)
    
    if imagen is None:
        print(f"⚠️ Error al leer la imagen {archivo}. Saltando...")
        continue

    # Le pasamos el recorte a YOLO
    resultados = modelo_vision(imagen, verbose=False, classes=CLASES_PERMITIDAS)
    
    producto_detectado = None
    mejor_confianza = 0.0

    # Buscamos qué ha visto con más seguridad
    for r in resultados:
        for caja in r.boxes:
            confianza = caja.conf[0].item()
            if confianza > mejor_confianza and confianza > 0.40: # Umbral relajado al 40%
                mejor_confianza = confianza
                clase_id = int(caja.cls[0].item())
                producto_detectado = modelo_vision.names[clase_id] # Devuelve 'apple', 'book', etc.

    # Interacción con la Base de Datos
    if producto_detectado:
        print(f"🔍 Foto [{archivo}] -> YOLO detectó: {producto_detectado.upper()} ({(mejor_confianza*100):.1f}%)")
        respuesta_bd = hri_super.procesar_peticion(producto_detectado)
        print(f"   💬 Respuesta BD: {respuesta_bd}")
    else:
        print(f"🔍 Foto [{archivo}] -> ❌ Descartado. YOLO no reconoció ningún producto válido.")

    # Movemos la foto a procesados para limpiar la bandeja de entrada
    ruta_destino = os.path.join(CARPETA_PROCESADOS, archivo)
    shutil.move(ruta_completa, ruta_destino)

print("-" * 50)
print(f"✅ Análisis Local completado. Carpetas actualizadas.")