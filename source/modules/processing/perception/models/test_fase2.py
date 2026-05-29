import sys
import os
import shutil
import PIL.Image
import google.generativeai as genai

# Forzamos la ruta raíz (5 niveles arriba)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))
from source.modules.processing.HRI.HRI_manager import SupermercadoHRI

print("🧠 Iniciando Fase 2 Cloud: Análisis con Gemini Vision...")

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS Y BD
# ==========================================
carpeta_actual = os.path.dirname(os.path.abspath(__file__))

# Rutas de las carpetas 
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
# 2. CONFIGURACIÓN DE LA API DE GEMINI
# ==========================================
# ⚠️ PON AQUÍ TU API KEY REAL
API_KEY = "AIzaSyBTwgytXG3GUqNVhnc3r9Z_BMWI6E-YURM" 
genai.configure(api_key=API_KEY)

# Usamos el modelo Flash porque es rapidísimo y súper barato para imágenes
modelo_vision = genai.GenerativeModel('gemini-2.0-flash')

# ==========================================
# 3. PROCESAMIENTO DE LAS FOTOS
# ==========================================
archivos_pendientes = [f for f in os.listdir(CARPETA_PENDIENTES) if f.endswith('.jpg') or f.endswith('.png')]

if not archivos_pendientes:
    print("✅ No hay recortes pendientes para analizar. El pasillo está procesado.")
    sys.exit()

print(f"📦 Se han encontrado {len(archivos_pendientes)} fotos pendientes. Subiendo a la nube...")
print("-" * 50)

# El truco maestro: obligar a la IA a que solo diga nuestras palabras clave
prompt_ingeniero = """
Eres el sistema visual de un robot de inventario.
Observa la imagen y dime qué producto es. 
Solo puedes responder con UNA de estas cuatro palabras exactas (en minúsculas), sin puntos ni texto extra:
- apple (si ves manzanas o fruta parecida)
- banana (si ves plátanos)
- bottle (si ves cualquier tipo de botella)
- book (si ves un libro, revista o caja rectangular que parezca un libro)

Si no logras distinguir nada, responde: desconocido
"""

for archivo in archivos_pendientes:
    ruta_completa = os.path.join(CARPETA_PENDIENTES, archivo)
    
    try:
        # Abrimos la imagen con la librería PIL (la favorita de Gemini)
        imagen = PIL.Image.open(ruta_completa)
        
        # Le enviamos la imagen y las instrucciones a Gemini
        respuesta = modelo_vision.generate_content([prompt_ingeniero, imagen])
        producto_detectado = respuesta.text.strip().lower()
        
        # Interacción con la Base de Datos
        if producto_detectado in ['apple', 'banana', 'bottle', 'book']:
            print(f"🔍 Foto [{archivo}] -> Gemini detectó: {producto_detectado.upper()}")
            respuesta_bd = hri_super.procesar_peticion(producto_detectado)
            print(f"   💬 Respuesta BD: {respuesta_bd}")
        else:
            print(f"🔍 Foto [{archivo}] -> ❌ Descartado. Gemini vio: {producto_detectado}")

        # Movemos la foto a procesados
        imagen.close() # Cerramos el archivo para poder moverlo
        ruta_destino = os.path.join(CARPETA_PROCESADOS, archivo)
        shutil.move(ruta_completa, ruta_destino)
        
    except Exception as e:
        print(f"⚠️ Error al procesar {archivo} con la API: {e}")

print("-" * 50)
print(f"✅ Análisis en la nube completado. Carpetas actualizadas.")