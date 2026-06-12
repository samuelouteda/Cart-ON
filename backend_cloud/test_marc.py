from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import json
import base64
import cv2
import numpy as np
import sys
from pathlib import Path

# Fix de rutes per trobar 'core' i 'db'
ruta_actual = str(Path(__file__).resolve().parent)
if ruta_actual not in sys.path:
    sys.path.insert(0, ruta_actual)

try:
    from core.config import Config
    from db.sql_manager import SQLManager
    print("[Cloud] ✅ Módulos 'Config' y 'SQLManager' importados.")
except ImportError:
    print("[Cloud] 🔴 Error d'importació de mòduls Cart-ON.")
    class Config: UAB_TOKEN = "accesoAlLLM"
    class SQLManager: pass

app = FastAPI()

try:
    sql_db = SQLManager()
except Exception as e:
    print(f"[Cloud] ⚠️ No inicialitzat SQLManager: {e}")
    sql_db = None

def vision_qwen_uab(base64_image: str):
    try:
        client = OpenAI(api_key=Config.UAB_TOKEN, base_url="https://dcc-llm.uab.cat/bes2/v1")
    except Exception as e:
        print(f"[Vision] 🔴 Error connexió: {e}")
        return []

    prompt_inventario = """
    Eres el sistema de visión artificial de un robot de inventario de supermercado.
    Identifica los productos en la imagen y cuéntalos.
    REGLA ESTRICTA: Responde ÚNICA Y EXCLUSIVAMENTE con un JSON válido que sea una lista de objetos.
    Cada objeto debe tener 'producto', 'cantidad' y 'caja' [y_min, x_min, y_max, x_max] (0 a 1000).
    Ejemplo: [{"producto": "Botella de agua", "cantidad": 1, "caja": [200, 300, 400, 600]}]
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
        
        if texto_crudo.startswith("```json"):
            texto_crudo = texto_crudo[7:-3].strip()
        elif texto_crudo.startswith("```"):
            texto_crudo = texto_crudo[3:-3].strip()
            
        return json.loads(texto_crudo)
    except Exception as e:
        print(f"❌ Error en LLM: {e}")
        return []

def procesar_y_dibujar_anotaciones(imagen_base64: str, detecciones: list) -> str:
    img_bytes = base64.b64decode(imagen_base64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    alto, ancho = img.shape[:2]

    for item in detecciones:
        caja = item.get("caja", [])
        if len(caja) == 4:
            y1, x1 = int(caja[0] * alto / 1000), int(caja[1] * ancho / 1000)
            y2, x2 = int(caja[2] * alto / 1000), int(caja[3] * ancho / 1000)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
            label = f"{item.get('producto', '???')} x{item.get('cantidad', 1)}"
            cv2.putText(img, label, (x1, max(y1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

def ejecutar_upsert_en_bd(nombre_producto: str, cantidad: int):
    if not sql_db or not nombre_producto: return
    try:
        conn = sql_db.get_connection() 
        if not conn: return
        cursor = conn.cursor()
        nombre_limpio = nombre_producto.strip().lower()
        
        query = """
            INSERT INTO productos (nombre_interno, nombre_pantalla, precio, stock_actual)
            VALUES (%s, %s, 0.00, %s)
            ON DUPLICATE KEY UPDATE stock_actual = stock_actual + %s;
        """
        cursor.execute(query, (nombre_limpio, nombre_producto.strip(), cantidad, cantidad))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"🗄️ [SQL Real] Upsert exitoso: {nombre_limpio} (+{cantidad})")
    except Exception as e:
        print(f"🗄️ [SQL Real] 🔴 ERROR MYSQL: {e}")

class Payload(BaseModel):
    imagen_base64: str

@app.post("/api/escanear")
async def recibir_escaneo(data: Payload):
    print("\n📥 [FastAPI] Petición entrante via JSON...")
    detecciones = vision_qwen_uab(data.imagen_base64)
    
    if not detecciones:
        raise HTTPException(status_code=500, detail="El modelo visual no devolvió detecciones.")
        
    for item in detecciones:
        nombre = item.get("producto", "")
        cantidad = int(item.get("cantidad", 1)) if str(item.get("cantidad")).isdigit() else 1
        if nombre:
            ejecutar_upsert_en_bd(nombre, cantidad)
            
    img_anotada_b64 = procesar_y_dibujar_anotaciones(data.imagen_base64, detecciones)
    return {
        "status": "ok",
        "detectado": detecciones,
        "imagen_anotada": img_anotada_b64
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("test_cloud:app", host="0.0.0.0", port=8000, reload=True)