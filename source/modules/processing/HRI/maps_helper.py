import requests
import numpy as np
import cv2
import qrcode

def generate_location_image(aula, lat, lng, api_key):
    """Descarga el mapa de Google Maps con coordenadas exactas y añade QR dinámico"""
    
    # 1. Enlace Oficial Universal de Google Maps para el QR
    # Obliga al móvil a abrir esa latitud y longitud exactas en la app nativa
    maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    
    # Generamos el QR
    qr = qrcode.make(maps_url)
    qr_cv = cv2.cvtColor(np.array(qr.convert('RGB')), cv2.COLOR_RGB2BGR)
    qr_cv = cv2.resize(qr_cv, (140, 140))

    # 2. Descargamos el Mapa Estático centrado en las coordenadas
    map_cv = np.zeros((300, 720, 3), dtype=np.uint8)
    
    if api_key:
        # Fíjate que center y markers ahora usan lat,lng. He puesto zoom=19 para que se vea el edificio súper de cerca.
        static_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lng}&zoom=19&size=720x300&maptype=roadmap&markers=color:red%7C{lat},{lng}&key={api_key}"
        try:
            resp = requests.get(static_url, timeout=5)
            resp.raise_for_status()
            img_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            map_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"🔴 Error cargando mapa: {e}")
            cv2.putText(map_cv, "Error descargando mapa", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
    else:
        cv2.putText(map_cv, "Falta MAPS_API_KEY en .env", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

    # 3. Fusión (Pegamos el QR en la esquina inferior derecha del mapa)
    h, w, _ = map_cv.shape
    qh, qw, _ = qr_cv.shape
    map_cv[h-qh-10 : h-10, w-qw-10 : w-10] = qr_cv

    # Añadimos texto con borde negro (para que se lea bien sobre cualquier fondo del mapa)
    cv2.putText(map_cv, "Escanea la ruta:", (w-qw-10, h-qh-20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)
    cv2.putText(map_cv, "Escanea la ruta:", (w-qw-10, h-qh-20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    return map_cv