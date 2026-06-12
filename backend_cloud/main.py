import base64
import io
from fastapi import FastAPI, UploadFile, File, Form
from orchestrator.cloud_planner import PlannerCloud
from gtts import gTTS

app = FastAPI(title="Cart-ON API Gateway")
planner = PlannerCloud()

@app.get("/")
def health_check():
    return {"status": "Cart-ON Cloud Brain is Online", "fase_actual": planner.estado_actual}

@app.post("/api/v1/interaccion")
async def endpoint_hri(
    frase_usuario: str = Form(...),
    image_file: UploadFile = File(...)
):
    try:
        imagen_bytes = await image_file.read()
        mime_type = image_file.content_type
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # 1. El orquestador decide y la IA redacta el texto
        respuesta_final = planner.procesar_peticion_hri(frase_usuario, base64_image, mime_type)
        
        # 2. TTS: Convertimos ese texto en un archivo de audio MP3
        texto = respuesta_final.get("texto", "")
        if texto:
            # lang='es' y tld='es' nos da el acento de España.
            tts = gTTS(text=texto, lang='es', tld='es')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            # Lo empaquetamos en texto Base64 para que viaje seguro por la red
            respuesta_final["audio_b64"] = base64.b64encode(fp.read()).decode('utf-8')

        return respuesta_final
    except Exception as e:
        return {"status": "error", "texto": f"Error en el servidor: {str(e)}"}