import os
import cv2
import mysql.connector
from queue import Queue
from dotenv import load_dotenv

# Importamos tus módulos reales
from modules.actuation.display import Display
from modules.actuation.maps_helper import generate_location_image

def obtener_coordenadas_db(aula):
    """Hace una consulta real a la BD para sacar las coordenadas del aula"""
    try:
        # 1. Conectamos a la BD (Usa los datos de tu nube)
        conexion = mysql.connector.connect(
            host=os.getenv("DB_HOST", "34.28.135.54"), 
            user=os.getenv("DB_USER", "marco-mejias"),
            password=os.getenv("DB_PASS", "cart-on-Fortnite67"),
            database=os.getenv("DB_NAME", "carton_db")
        )
        cursor = conexion.cursor(dictionary=True)
        
        # 2. Hacemos la consulta a la nueva tabla
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

def probar_mapa():
    print("🚀 Iniciando prueba de Interfaz, SQL y Google Maps...")
    
    # Cargamos el .env
    load_dotenv()
    maps_key = os.getenv("MAPS_API_KEY")

    # Inicializamos pantalla
    bus_falso = Queue()
    pantalla = Display("DisplayTest", bus_falso, {})
    
    # --- PRUEBA CON BD ---
    aula_prueba = "Q4/0015"
    print(f"📡 Buscando coordenadas de {aula_prueba} en MySQL...")
    
    lat_prueba, lng_prueba = obtener_coordenadas_db(aula_prueba)
    
    if lat_prueba and lng_prueba:
        print(f"✅ ¡Encontrado! Lat: {lat_prueba}, Lng: {lng_prueba}")
        print("🗺️ Descargando mapa de Google...")
        
        # Llamamos a Google Maps con los datos vivos de la BD
        imagen_mapa = generate_location_image(aula_prueba, lat_prueba, lng_prueba, maps_key)
        
        pantalla.update_data(
            status="SUCCESS",
            title=f"Ruta generada: Aula {aula_prueba}",
            text="¿Dónde está la clase de visión por computador?",
            robot_text="La clase es en el aula Q4/0015. He descargado las coordenadas exactas de la base de datos. ¡Escanea el QR!",
            image=imagen_mapa
        )
    else:
        # Si falla la BD, mostramos error en pantalla
        pantalla.update_data(
            status="ERROR",
            title="Fallo de Base de Datos",
            robot_text="No he podido encontrar esa aula en la tabla aulas_uab."
        )
    
    print("👉 Pulsa CUALQUIER TECLA (con la ventana seleccionada) para cerrar.")
    
    while True:
        pantalla.refresh()
        if cv2.waitKey(100) != -1: 
            break
            
    pantalla.close()
    print("🛑 Prueba finalizada limpiamente.")

if __name__ == "__main__":
    probar_mapa()