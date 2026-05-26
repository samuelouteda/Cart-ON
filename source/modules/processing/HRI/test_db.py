import os
import mysql.connector
from HRI import HRI

print("\n" + "="*50)
print(" 🧠 INICIANDO CONEXIÓN CEREBRAL: HRI <-> CLOUD SQL 🧠")
print("="*50)

# 1. --- CONFIGURACIÓN DE CLAVES ---
API_KEY_GEMINI = "AIzaSyBTwgytXG3GUqNVhnc3r9Z_BMWI6E-YURM"

# 2. --- CREDENCIALES DE BASE DE DATOS ---
DB_HOST = "34.28.135.54"      # La IP de tu máquina en Google Cloud
DB_USER = "marco-mejias"      # Tu usuario de la BBDD
DB_PASS = "cart-on-Fortnite67"     # La contraseña de ese usuario
DB_NAME = "carton_db"         # El nombre de la base de datos

# Bus falso para que HRI no se queje
class MockEventBus:
    def put(self, event): pass

mock_bus = MockEventBus()
mock_stream = {"audio": None, "frame": None}

print("\n[1] Arrancando Inteligencia Artificial (Gemini)...")
cerebro_nlp = HRI("HRI_Test", mock_bus, mock_stream, "stt_key_dummy", API_KEY_GEMINI)

print("[2] Conectando a la Base de Datos (Google Cloud)...")
try:
    conexion_db = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    cursor = conexion_db.cursor(dictionary=True)
    print(" 🟢 ¡Conexión a la nube establecida!")
except Exception as e:
    print(f" 🔴 Error conectando a la BBDD: {e}")
    exit()

print("\n" + "="*50)
print(" 🗣️ CHAT CON EL ROBOT (Escribe 'salir' para terminar)")
print("="*50)

while True:
    frase = input("\nTú: ")
    if frase.lower() in ['salir', 'exit', 'quit']:
        break

    # 1. Mandamos la frase a Gemini
    intent, item, quantity, reply = cerebro_nlp.parse_intent(frase)
    
    print(f" 🤖 Intent detectado: {intent} | Producto: {item}")

    # 2. Lógica del "Planner" según la intención
    if intent == "read" and item:
        # Buscamos el producto en la base de datos usando "LIKE" para que sea flexible
        query = "SELECT nombre_pantalla, stock_actual FROM productos WHERE sinonimos LIKE %s OR nombre_pantalla LIKE %s"
        valor_busqueda = f"%{item.lower()}%"
        
        cursor.execute(query, (valor_busqueda, valor_busqueda))
        resultados = cursor.fetchall()

        if resultados:
            for fila in resultados:
                print(f" 🛒 [BASE DE DATOS]: Nos quedan {fila['stock_actual']} unidades de {fila['nombre_pantalla']}.")
        else:
            print(f" ❓ [BASE DE DATOS]: No encuentro '{item}' en el inventario del supermercado.")
            
    elif intent == "chat" and reply:
        print(f" 🤖 Cart-ON: {reply}")
        
    elif intent == "unknown":
        print(" 🤖 Cart-ON: No te he entendido bien, ¿puedes repetirlo?")
        
    else:
        print(f" ⚙️ [SISTEMA]: Operación '{intent}' recibida para '{item}', pero este test solo lee stock (read).")

# Cerrar conexiones al salir
cursor.close()
conexion_db.close()
print("\nApagando sistemas... ¡Test finalizado!")