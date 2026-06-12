import os
import cv2
import numpy as np
import mysql.connector
import serial
import json
import time
import textwrap # 👈 ¡La librería mágica que arregla el texto salido de los bordes!
from queue import Queue
from dotenv import load_dotenv

from modules.actuation.display import Display
from modules.actuation.maps_helper import generate_location_image

# 🔌 CONFIGURACIÓN DE LA PANTALLA LILYGO
PUERTO_LILYGO = 'COM3'     # Asegúrate de que es tu puerto
BAUD_RATE_LILYGO = 2000000 

# ==========================================
# 📺 FUNCIONES DE LA LILYGO Y DISEÑO UI
# ==========================================
# ==========================================
# 📺 FUNCIONES DE LA LILYGO Y DISEÑO UI MEJORADO
# ==========================================
def componer_lienzo_completo(titulo, imagen_mapa):
    """Lienzo minimalista: Solo Título grande y Mapa Gigante."""
    # 1. Crear lienzo blanco gigante (540 alto, 960 ancho)
    lienzo = np.ones((540, 960, 3), dtype=np.uint8) * 255
    
    # 2. Escribir el Título grande en la parte superior
    cv2.putText(lienzo, titulo, (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 4)
    
    # 3. Pegar el Mapa (Haciéndolo lo más grande posible)
    if imagen_mapa is not None:
        alto_mapa, ancho_mapa = imagen_mapa.shape[:2]
        
        # Le damos un espacio gigantesco (900 de ancho x 440 de alto)
        max_w, max_h = 900, 440
        
        # Calculamos la escala para no deformar el mapa y que encaje perfecto
        escala = min(max_w / ancho_mapa, max_h / alto_mapa)
        nuevo_ancho = int(ancho_mapa * escala)
        nuevo_alto = int(alto_mapa * escala)
        
        # Redimensionamos con alta calidad
        mapa_redimensionado = cv2.resize(imagen_mapa, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)
        
        # Matemáticas para centrar el mapa perfectamente debajo del título
        x_offset = (960 - nuevo_ancho) // 2
        y_offset = 80 + (440 - nuevo_alto) // 2 
        
        # Inyectar los píxeles del mapa gigante en el lienzo
        lienzo[y_offset:y_offset+nuevo_alto, x_offset:x_offset+nuevo_ancho] = mapa_redimensionado
        
    return lienzo


def empaquetar_imagen_lilygo(img_cv2):
    """Convierte el lienzo OpenCV a escala de grises de 4-bits."""
    img_gray = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2GRAY)
    img_16_tonos = (img_gray // 16).astype(np.uint8)
    
    pixeles_izquierdos = img_16_tonos[:, 0::2]
    pixeles_derechos = img_16_tonos[:, 1::2]
    imagen_empaquetada = (pixeles_izquierdos << 4) | pixeles_derechos
    return imagen_empaquetada.tobytes()

def enviar_imagen_lilygo(datos_binarios):
    """Protocolo Ping-Pong blindado para mandar el lienzo a la pantalla."""
    try:
        conexion = serial.Serial()
        conexion.port = PUERTO_LILYGO
        conexion.baudrate = BAUD_RATE_LILYGO
        conexion.timeout = 8
        conexion.setDTR(False)
        conexion.setRTS(False)
        conexion.open()
        conexion.reset_input_buffer()
        conexion.reset_output_buffer()
        time.sleep(1)

        print("📡 Sincronizando con LilyGO...")
        conexion.write((json.dumps({"type": "image"}) + "\n").encode('utf-8'))
        
        if "READY" in conexion.readline().decode('utf-8').strip():
            tamano_bloque = 4096
            for i in range(0, len(datos_binarios), tamano_bloque):
                bloque = datos_binarios[i : i + tamano_bloque]
                conexion.write(bloque)
                if conexion.readline().decode('utf-8').strip() != "NEXT":
                    break
            print(f"🤖 [LILYGO]: {conexion.readline().decode('utf-8').strip()}")
        conexion.close()
    except Exception as e:
        print(f"🔴 Error enviando imagen a LilyGO: {e}")

# ==========================================
# 🚀 LÓGICA PRINCIPAL (TU CÓDIGO)
# ==========================================
def obtener_coordenadas_db(aula):
    try:
        conexion = mysql.connector.connect(
            host=os.getenv("DB_HOST", "34.28.135.54"), 
            user=os.getenv("DB_USER", "marco-mejias"),
            password=os.getenv("DB_PASS", "cart-on-Fortnite67"),
            database=os.getenv("DB_NAME", "carton_db")
        )
        cursor = conexion.cursor(dictionary=True)
        query = "SELECT latitud, longitud FROM aulas_uab WHERE nombre_aula = %s"
        cursor.execute(query, (aula,))
        resultado = cursor.fetchone()
        
        cursor.close()
        conexion.close()
        
        if resultado:
            return float(resultado['latitud']), float(resultado['longitud'])
        else:
            print(f"⚠️ El aula '{aula}' no existe en la BD.")
            return None, None
    except Exception as e:
        print(f"🔴 Error de conexión SQL en el test: {e}")
        return None, None

# ... (Las funciones empaquetar_imagen_lilygo y enviar_imagen_lilygo se quedan IGUAL) ...

def probar_mapa():
    print("🚀 Iniciando prueba minimalista de LilyGO y Maps...")
    load_dotenv()
    maps_key = os.getenv("MAPS_API_KEY")

    bus_falso = Queue()
    pantalla = Display("DisplayTest", bus_falso, {})
    
    aula_prueba = "Q4/0015"
    print(f"📡 Buscando coordenadas de {aula_prueba} en MySQL...")
    lat_prueba, lng_prueba = obtener_coordenadas_db(aula_prueba)
    
    if lat_prueba and lng_prueba:
        print(f"✅ ¡Encontrado! Lat: {lat_prueba}, Lng: {lng_prueba}")
        print("🗺️ Descargando mapa de Google...")
        
        # 1. Generamos el mapa
        imagen_mapa = generate_location_image(aula_prueba, lat_prueba, lng_prueba, maps_key)
        
        # El título limpio que saldrá en la pantalla
        titulo = f"Ruta generada: Aula {aula_prueba}"
        
        # 2. Actualizamos la pantalla de tu PC
        pantalla.update_data(
            status="SUCCESS",
            title=titulo,
            text="¿Dónde está la clase?",
            robot_text="La clase es en el aula Q4/0015. ¡Escanea el QR!",
            image=imagen_mapa
        )
        
        # 3. 🚀 MAGIA LILYGO: Lienzo limpio (Solo Título + Mapa Gigante)
        print("🎨 Preparando lienzo minimalista para Tinta Electrónica...")
        lienzo_final = componer_lienzo_completo(titulo, imagen_mapa)
        
        paquete_binario = empaquetar_imagen_lilygo(lienzo_final)
        enviar_imagen_lilygo(paquete_binario)
        
    else:
        # Modo error limpio
        titulo_err = "Fallo de Base de Datos"
        texto_err = "Aula no encontrada."
        pantalla.update_data(status="ERROR", title=titulo_err, robot_text=texto_err)
        
        # Reutilizamos la función aunque no haya mapa (pasando None)
        lienzo_error = componer_lienzo_completo(titulo_err + ": " + texto_err, None)
        enviar_imagen_lilygo(empaquetar_imagen_lilygo(lienzo_error))
    
    print("👉 Pulsa CUALQUIER TECLA (con la ventana seleccionada) para cerrar.")
    while True:
        pantalla.refresh()
        if cv2.waitKey(100) != -1: 
            break
            
    pantalla.close()
    print("🛑 Prueba finalizada limpiamente.")

if __name__ == "__main__":
    probar_mapa()