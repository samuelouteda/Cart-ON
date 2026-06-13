import base64
import io
import json
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
    lista_compra: str = Form("{}"), # Recibimos la lista como string JSON
    image_file: UploadFile = File(...)
):
    try:
        imagen_bytes = await image_file.read()
        mime_type = image_file.content_type
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # Transformamos el string JSON a un diccionario de Python
        lista_compra_local = json.loads(lista_compra) if lista_compra else {}
        
        # 1. El orquestador decide, actualiza la lista y la IA redacta el texto
        respuesta_final = planner.procesar_peticion_hri(
            texto_usuario=frase_usuario, 
            imagen_bytes=base64_image, 
            mime_type=mime_type, 
            lista_compra_local=lista_compra_local
        )
        
        # EL CHIVATO ESTELAR: Verás el JSON de la lista de la compra actualizado aquí
        print("\n" + "="*15)
        print(f"CHIVATO 3 [FastAPI Final Output]:\n{respuesta_final}")
        print("="*15 + "\n")
        
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
        print(f"Error crítico en FastAPI: {e}")
        # Salvavidas para que la Raspberry no crashee si algo peta fuerte
        return {
            "status": "error", 
            "texto": f"Error en el servidor: {str(e)}", 
            "emocion": "triste"
        }