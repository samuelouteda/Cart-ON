import base64
from fastapi import FastAPI, UploadFile, File, Form
from modules.decision_making.planner import PlannerCloud

app = FastAPI(title="Cart-ON API Gateway")

# Instanciamos el Cerebro Central una sola vez al arrancar el servidor
planner = PlannerCloud()

@app.get("/")
def health_check():
    return {"status": "Cart-ON Cloud Brain is Online", "fase_actual": planner.estado_actual}

@app.post("/api/v1/interaccion")
async def endpoint_hri(
    frase_usuario: str = Form(...),
    image_file: UploadFile = File(...)
):
    """
    Ruta para la Fase 2 (Interacción Humano-Robot).
    Recibe el audio/texto y la cámara frontal.
    """
    try:
        imagen_bytes = await image_file.read()
        mime_type = image_file.content_type
        
        # Le pasamos el paquete en crudo (base64) al Planner y que él se apañe
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        respuesta_final = planner.procesar_peticion_hri(frase_usuario, base64_image, mime_type)
        return respuesta_final

    except Exception as e:
        return {"status": "error", "texto": f"Error en la capa de red: {str(e)}"}

# ⚠️ Aquí añadiremos en el futuro @app.post("/api/v1/escaneo") para la Fase 1