import base64
import io
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from orchestrator.cloud_planner import PlannerCloud
from gtts import gTTS

app = FastAPI(title="Cart-ON API Gateway")
planner = PlannerCloud()

# Estructura de datos que recibe el escaneo
class PayloadEscaneo(BaseModel):
    imagen_base64: str
    robot_x: float = 0.0
    robot_y: float = 0.0

@app.get("/")
def health_check():
    return {"status": "Cart-ON Cloud Brain is Online", "fase_actual": planner.estado_actual}

# ==========================================
# ENDPOINT 1: VOZ DEL ROBOT
# ==========================================
@app.post("/api/v1/interaccion")
async def endpoint_hri(
    frase_usuario: str = Form(...),
    lista_compra: str = Form("{}"),
    image_file: UploadFile = File(...)
):
    try:
        imagen_bytes = await image_file.read()
        mime_type = image_file.content_type
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        lista_compra_local = json.loads(lista_compra) if lista_compra else {}
        
        respuesta_final = planner.procesar_peticion_hri(
            texto_usuario=frase_usuario, 
            imagen_bytes=base64_image, 
            mime_type=mime_type, 
            lista_compra_local=lista_compra_local
        )
        
        texto = respuesta_final.get("texto", "")
        if texto:
            tts = gTTS(text=texto, lang='es', tld='es')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            respuesta_final["audio_b64"] = base64.b64encode(fp.read()).decode('utf-8')

        return respuesta_final
    except Exception as e:
        print(f"Error crítico en FastAPI: {e}")
        return {"status": "error", "texto": "Error en el servidor.", "emocion": "triste"}

# ==========================================
# ENDPOINT 2: ESCANEO DE ESTANTERÍAS
# ==========================================
@app.post("/api/v1/escaneo_inventario")
async def endpoint_escaneo(data: PayloadEscaneo):
    try:
        resultado = planner.procesar_escaneo_estanteria(
            imagen_base64=data.imagen_base64,
            robot_x=data.robot_x,
            robot_y=data.robot_y
        )
        if not resultado.get("detectado"):
            raise HTTPException(status_code=500, detail="Qwen no detectó productos válidos.")
        return resultado
    except Exception as e:
        print(f"Error procesando escaneo: {e}")
        raise HTTPException(status_code=500, detail=str(e))