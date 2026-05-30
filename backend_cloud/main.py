from fastapi import FastAPI, UploadFile, File, Form
from google import genai
import PIL.Image
import io

app = FastAPI(title="Cart-ON Backend Cloud")

# ⚠️ PON AQUÍ TU API KEY DE GEMINI
API_KEY = "AIzaSyB7WRVRZnDipGicwVpcMI9alm1sRvMpWwc"
client = genai.Client(api_key=API_KEY)

# El prompt estricto que ya diseñamos
PROMPT_VISION = """
Eres el sistema visual de un robot de inventario.
Observa la imagen y dime qué producto es. 
Solo puedes responder con UNA de estas cuatro palabras exactas (en minúsculas), sin puntos ni texto extra:
- apple 
- banana 
- bottle 
- book 

Si no logras distinguir nada, responde: desconocido
"""

@app.get("/")
def ping():
    return {"status": "ok", "mensaje": "Servidor activo."}

@app.post("/api/v1/ask")
async def procesar_peticion_robot(
    image_file: UploadFile = File(...),
    texto_debug: str = Form("sin_texto")
):
    print(f"📥 Petición recibida. Analizando foto: {image_file.filename}")
    
    try:
        # 1. Leemos la imagen que nos acaba de mandar el robot por internet
        imagen_bytes = await image_file.read()
        imagen_pil = PIL.Image.open(io.BytesIO(imagen_bytes))
        
        # 2. Se la mandamos a Gemini
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[PROMPT_VISION, imagen_pil]
        )
        
        producto_detectado = response.text.strip().lower()
        print(f"👁️ Gemini ha visto: {producto_detectado}")
        
        # 3. Devolvemos la respuesta real al robot
        return {
            "status": "success",
            "producto_detectado": producto_detectado,
            "texto": f"He analizado la imagen y veo: {producto_detectado.upper()}"
        }
        
    except Exception as e:
        return {"status": "error", "texto": f"Error procesando la imagen: {str(e)}"}