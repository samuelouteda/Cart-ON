import os
import requests
import cv2
import numpy as np
import qrcode

def generate_location_image(aula_nombre, lat, lng, api_key=None):
    """
    Se descarga el mapa estático de Google Maps, genera un QR de navegación
    y los fusiona en una sola imagen lista para OpenCV (Display).
    """
    if not api_key:
        api_key = os.getenv("MAPS_API_KEY", "TU_API_KEY_POR_DEFECTO")

    print(f"[MapsHelper] Generando mapa para {aula_nombre} ({lat}, {lng})...")

    # 1. DESCARGAR MAPA ESTÁTICO DE GOOGLE
    # Modifica size=600x400 o zoom=18 si lo ves pequeño en tu pantalla grande
    url_mapa = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={lat},{lng}&zoom=18&size=600x400&maptype=roadmap"
        f"&markers=color:red%7Clabel:A%7C{lat},{lng}&key={api_key}"
    )

    mapa_img = None
    try:
        res = requests.get(url_mapa, timeout=10)
        if res.status_code == 200:
            # Convertimos los bytes descargados en una matriz de OpenCV (BGR)
            arr = np.asarray(bytearray(res.content), dtype=np.uint8)
            mapa_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        else:
            print(f"[MapsHelper] Error API Google Estática (Status: {res.status_code})")
    except Exception as e:
        print(f"[MapsHelper] Error de red al descargar mapa: {e}")

    # Si Google Maps falla, creamos un fondo negro de seguridad para que no crashee la pantalla
    if mapa_img is None:
        mapa_img = np.zeros((400, 600, 3), dtype=np.uint8)
        cv2.putText(mapa_img, "Mapa No Disponible", (150, 200), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # 2. GENERAR CÓDIGO QR CON LA URL REAL DE GOOGLE MAPS
    # Esto genera el enlace directo de navegación GPS para el móvil del estudiante
    url_navegacion = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url_navegacion)
    qr.make(fit=True)
    
    qr_img_plana = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    # Convertimos la imagen de la librería QR al formato de OpenCV (BGR)
    qr_img_cv = cv2.cvtColor(np.array(qr_img_plana), cv2.COLOR_RGB2BGR)
    # Redimensionamos el QR para que encaje estéticamente al lado del mapa
    qr_img_cv = cv2.resize(qr_img_cv, (400, 400))

    # 3. FUSIONAR MAPA Y QR (Uno al lado del otro horizontalmente)
    # Alto total: 400px. Ancho total: 600px (mapa) + 400px (QR) = 1000px
    imagen_final_fusionada = np.hstack((mapa_img, qr_img_cv))
    
    return imagen_final_fusionada