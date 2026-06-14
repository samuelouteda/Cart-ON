from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import json
import base64
import cv2
import numpy as np

# 🛠️ IMPORTACIONES REALES DE TU PROYECTO CART-ON
try:
    from core.config import Config
    from db.sql_manager import SQLManager
    print("[TestCloud] Módulos 'Config' y 'SQLManager' importados correctamente.")
except ImportError:
    print("[TestCloud] Error: No se pudo importar la estructura de Cart-ON.")
    print("Asegúrate de ejecutar uvicorn desde la raíz del proyecto o añade las rutas.")
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
# 1. MOTOR VISUAL (UAB LLM - Modelo-bXs2)
# ==========================================
def vision_qwen_uab(base64_image: str):
    try:
        client = OpenAI(api_key=Config.UAB_TOKEN, base_url="https://dcc-llm.uab.cat/bes2/v1")
    except Exception as e:
        print(f"[Vision] Error al conectar con el cliente OpenAI: {e}")
        return []

    # Forzamos el formato nativo de Qwen [ymin, xmin, ymax, xmax] de 0 a 1000
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
        print(f"[UAB LLM Raw Response]:\n{texto_crudo}\n")
        
        if texto_crudo.startswith("```json"):
            texto_crudo = texto_crudo[7:-3].strip()
        elif texto_crudo.startswith("```"):
            texto_crudo = texto_crudo[3:-3].strip()
            
        return json.loads(texto_crudo)
    except Exception as e:
        print(f"Error en la inferencia del LLM: {e}")
        return []

# ==========================================
# 2. PROCESAMIENTO Y DIBUJO DE BOUNDING BOXES
# ==========================================
def procesar_y_dibujar_anotaciones(imagen_base64: str, detecciones: list) -> str:
    # Decodificamos el Base64 entrante a matriz OpenCV
    img_bytes = base64.b64decode(imagen_base64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    alto, ancho = img.shape[:2]

    for item in detecciones:
        caja = item.get("caja", [])
        if len(caja) == 4:
            # Qwen-VL devuelve de forma nativa [ymin, xmin, ymax, xmax] escalado a 1000
            y1 = int(caja[0] * alto / 1000)
            x1 = int(caja[1] * ancho / 1000)
            y2 = int(caja[2] * alto / 1000)
            x2 = int(caja[3] * ancho / 1000)
            
            # Dibujamos el rectángulo verde de la Bounding Box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            # Colocamos la etiqueta del producto encima de la caja
            label = f"{item.get('producto', '???')} x{item.get('cantidad', 1)}"
            cv2.putText(img, label, (x1, max(y1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Volvemos a empaquetar la imagen pintada en Base64 para mandársela al robot
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

# ==========================================
# 3. CONEXIÓN DIRECTA A TU BASE DE DATOS SQL
# ==========================================
def ejecutar_upsert_en_bd(nombre_producto: str, cantidad: int):
    """
    Ejecuta el Upsert directamente en tu base de datos utilizando la 
    conexión de tu SQLManager.
    """
    if not sql_db or not nombre_producto:
        print("[SQL] No se puede guardar: SQLManager no está listo o nombre vacío.")
        return
        
    try:
        # Obtenemos la conexión real del SQLManager
        conn = sql_db.get_connection() 
        if not conn:
            print("[SQL] Error: No se pudo obtener una conexión activa de SQLManager.")
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
        # Imprimimos el error real que devuelve MySQL (ej. "Table 'productes' doesn't exist" o "Unknown column...")
        print(f"🗄️ [SQL Real] ERROR CRÍTICO DE MYSQL: {e}")
        print(f"   Intentando insertar -> Producto: '{nombre_producto}', Cantidad: {cantidad}")
        
    except Exception as e:
        print(f"🗄️ [SQL Real] Error al escribir en la BD: {e}")

# ==========================================
# 4. ENDPOINT FASTAPI
# ==========================================
class Payload(BaseModel):
    imagen_base64: str

@app.post("/api/test-scan")
async def recibir_escaneo(data: Payload):
    print("\n📥 [FastAPI] Petición de escaneo entrante...")
    
    # 1. Obtenemos las detecciones desde el servidor de la UAB
    detecciones = vision_qwen_uab(data.imagen_base64)
    
    if not detecciones:
        raise HTTPException(status_code=500, detail="El modelo visual no devolvió detecciones válidas.")
        
    # 2. Guardamos de verdad en la Base de Datos (Cloud SQL)
    for item in detecciones:
        nombre = item.get("producto", "")
        try:
            cantidad = int(item.get("cantidad", 1))
        except ValueError:
            cantidad = 1
            
        if nombre:
            ejecutar_upsert_en_bd(nombre, cantidad)
            
    # 3. Pintamos las cajitas usando la escala 1000 corregida
    img_anotada_b64 = procesar_y_dibujar_anotaciones(data.imagen_base64, detecciones)
    
    print("Procesamiento completado. Devolviendo imagen anotada al robot.")
    return {
        "status": "ok",
        "detectado": detecciones,
        "imagen_anotada": img_anotada_b64
    }