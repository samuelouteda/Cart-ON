from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import json
import base64
import cv2
import numpy as np
import subprocess
import time
import sys
from pathlib import Path

# ==========================================
# 🛠️ ARRANJAMENT DE RUTES PER EVITAR L'ERROR D'IMPORTACIÓ
# ==========================================
# Afegim la carpeta actual al path del sistema perquè trobi 'core' i 'db'
ruta_actual = str(Path(__file__).resolve().parent)
if ruta_actual not in sys.path:
    sys.path.insert(0, ruta_actual)

# 🛠️ IMPORTACIONES REALES DE TU PROYECTO CART-ON
try:
    from core.config import Config
    from db.sql_manager import SQLManager
    print("[TestCloud] ✅ Módulos 'Config' y 'SQLManager' importados correctamente.")
except ImportError:
    print("[TestCloud] 🔴 Error: No se pudo importar la estructura de Cart-ON de forma directa.")
    # Fallback seguro para que el archivo no crashee al levantar si hay problemas de paths
    class Config: UAB_TOKEN = "accesoAlLLM"
    class SQLManager: pass

app = FastAPI()

# Inicializamos tu gestor de base de datos real
try:
    sql_db = SQLManager()
except Exception as e:
    print(f"[TestCloud] ⚠️ No se pudo inicializar SQLManager: {e}")
    sql_db = None


# ==========================================
# 🛠️ FUNCIÓN DE DETECCIÓN Y CAPTURA AUTOMÁTICA DE HARDWARE
# ==========================================
def capturar_desde_hardware_disponible() -> bytes:
    """
    Intenta capturar una imagen usando el hardware disponible en la Raspberry Pi.
    Prueba primero con rpicam-still (sensor nativo) y si falla, recurre a OpenCV V4L2.
    Devuelve los bytes en bruto de la imagen JPEG.
    """
    print("🔍 [Cámara] Detectando hardware de captura...")
    
    # --- MÈTODE 1: Sensor Nativo / Sunny via rpicam-still ---
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
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print(f"⚠️ El sensor nativo (rpicam-still) no respondió o no está disponible.")

    # --- MÈTODE 2: Alternativa OpenCV genérica (V4L2 / USB / Webcams) ---
    try:
        print("📹 Intentando captura genérica mediante OpenCV (V4L2)...")
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
                print("✅ Captura exitosa con OpenCV backend V4L2.")
                return buffer.tobytes()
        else:
            cap.release()
    except Exception as e:
        print(f"⚠️ El método alternativo de OpenCV también falló: {e}")

    raise RuntimeError("No se detectó ninguna cámara funcional en los puertos del sistema.")


# ==========================================
# 1. MOTOR VISUAL (UAB LLM - Modelo-bXs2)
# ==========================================
def vision_qwen_uab(base64_image: str):
    try:
        client = OpenAI(api_key=Config.UAB_TOKEN, base_url="https://dcc-llm.uab.cat/bes2/v1")
    except Exception as e:
        print(f"[Vision] 🔴 Error al conectar con el cliente OpenAI: {e}")
        return []

    prompt_inventario = """
    Eres el sistema de visión artificial de un robot de inventario de supermercado.
    Identifica los productos en la imagen y cuéntalos.
    
    REGLA ESTRICTA: Responde ÚNICA Y EXCLUSIVAMENTE con un JSON válido que sea una lista de objetos.
    Cada objeto debe tener 'producto', 'cantidad' y 'caja'.
    El campo 'caja' debe contener [y_min, x_min, y_max, x_max] en un rango de 0 a 1000.
    
    Ejemplo: [{"producto": "Botella de agua", "cantidad": 1, "caja": [200, 300, 400, 600]}]
    No añadas texto introductorio ni bloques de formato Markdown.
    """

    try:
        response = client.chat.completions.create(
            model="Modelo-bXs2",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt_inventario},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}],
            temperature=0.01
        )
        
        texto_crudo = response.choices[0].message.content.strip()
        print(f"🤖 [UAB LLM Raw Response]:\n{texto_crudo}\n")
        
        if texto_crudo.startswith("```json"):
            texto_crudo = texto_crudo[7:-3].strip()
        elif texto_crudo.startswith("```"):
            texto_crudo = texto_crudo[3:-3].strip()
            
        return json.loads(texto_crudo)
    except Exception as e:
        print(f"❌ Error en la inferencia del LLM: {e}")
        return []

# ==========================================
# 2. PROCESAMIENTO Y DIBUJO DE BOUNDING BOXES
# ==========================================
def procesar_y_dibujar_anotaciones(imagen_base64: str, detecciones: list) -> str:
    img_bytes = base64.b64decode(imagen_base64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    alto, ancho = img.shape[:2]

    for item in detecciones:
        caja = item.get("caja", [])
        if len(caja) == 4:
            y1 = int(caja[0] * alto / 1000)
            x1 = int(caja[1] * ancho / 1000)
            y2 = int(caja[2] * alto / 1000)
            x2 = int(caja[3] * ancho / 1000)
            
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
            label = f"{item.get('producto', '???')} x{item.get('cantidad', 1)}"
            cv2.putText(img, label, (x1, max(y1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

# ==========================================
# 3. CONEXIÓN DIRECTA A TU BASE DE DATOS SQL
# ==========================================
def ejecutar_upsert_en_bd(nombre_producto: str, cantidad: int):
    if not sql_db or not nombre_producto:
        print("[SQL] ⚠️ No se puede guardar: SQLManager no está listo o nombre vacío.")
        return
        
    try:
        conn = sql_db.get_connection() 
        if not conn:
            print("[SQL] 🔴 Error: No se pudo obtener una conexión activa de SQLManager.")
            return
            
        cursor = conn.cursor()
        nombre_limpio = nombre_producto.strip().lower()
        
        query = """
            INSERT INTO productos (nombre_yolo, nombre_pantalla, precio, stock_actual)
            VALUES (%s, %s, 0.00, %s)
            ON DUPLICATE KEY UPDATE stock_actual = stock_actual + %s;
        """
        
        cursor.execute(query, (nombre_limpio, nombre_producto.strip(), cantidad, cantidad))
        conn.commit()
        
        cursor.close()
        conn.close()
        print(f"🗄️ [SQL Real] Upsert exitoso: {nombre_limpio} (+{cantidad})")
        
    except Exception as e:
        print(f"🗄️ [SQL Real] 🔴 ERROR CRÍTICO DE MYSQL: {e}")

# ==========================================
# 4. ENDPOINTS FASTAPI
# ==========================================
class Payload(BaseModel):
    imagen_base64: str

@app.post("/api/test-scan")
@app.post("/api/escanear")
async def recibir_escaneo(data: Payload):
    print("\n📥 [FastAPI] Petición de escaneo entrante via JSON...")
    return await procesar_flujo_completo(data.imagen_base64)


@app.post("/api/escanear-local")
async def escanear_usando_hardware_pi():
    print("\n📸 [FastAPI] Petición local recibida. Buscando cámara...")
    try:
        bytes_foto = capturar_desde_hardware_disponible()
        imagen_local_b64 = base64.b64encode(bytes_foto).decode('utf-8')
        print("✅ [FastAPI] Foto obtenida con éxito del hardware activo. Procesando flujo visual...")
        return await procesar_flujo_completo(imagen_local_b64)
    except RuntimeError as e:
        print(f"🔴 Error de hardware en el sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"🔴 Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def procesar_flujo_completo(imagen_b64: str):
    detecciones = vision_qwen_uab(imagen_b64)
    if not detecciones:
        raise HTTPException(status_code=500, detail="El modelo visual no devolvió detecciones válidas.")
        
    for item in detecciones:
        nombre = item.get("producto", "")
        try:
            cantidad = int(item.get("cantidad", 1))
        except ValueError:
            cantidad = 1
            
        if nombre:
            ejecutar_upsert_en_bd(nombre, cantidad)
            
    img_anotada_b64 = procesar_y_dibujar_anotaciones(imagen_b64, detecciones)
    print("🚀 Procesamiento completado. Inventario actualizado.")
    return {
        "status": "ok",
        "detectado": detecciones,
        "imagen_anotada": img_anotada_b64
    }

# Código para que funcione con `python3` directamente sin dar errores
if __name__ == "__main__":
    import uvicorn
    print("🚀 Levantando el servidor local de Cart-ON...")
    uvicorn.run("test_camera&yoloFalse:app", host="0.0.0.0", port=8000, reload=True)