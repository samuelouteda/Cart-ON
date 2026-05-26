import os
import mysql.connector
from HRI import HRI

print("\n" + "="*50)
print(" 📝 INICIANDO SIMULADOR DE LISTA DE LA COMPRA 📝")
print("="*50)

# 1. --- CONFIGURACIÓN ---
API_KEY_GEMINI = "AIzaSyBTwgytXG3GUqNVhnc3r9Z_BMWI6E-YURM"
DB_HOST = "34.28.135.54"
DB_USER = "marco-mejias"
DB_PASS = "cart-on-Fortnite67"
DB_NAME = "carton_db"

# 2. --- LA MEMORIA TEMPORAL DEL ROBOT ---
mi_lista = {}  # Diccionario para guardar {producto: cantidad}

class MockEventBus:
    def put(self, event): pass

print("\n[1] Arrancando Cerebro (Gemini)...")
cerebro_nlp = HRI("HRI_Test", MockEventBus(), {"audio": None, "frame": None}, "dummy", API_KEY_GEMINI)

print("[2] Conectando a Google Cloud SQL...")
try:
    conexion_db = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conexion_db.cursor(dictionary=True)
    print(" 🟢 ¡Conexión lista!")
except Exception as e:
    print(f" 🔴 Error BBDD: {e}"); exit()

print("\n" + "="*50)
print(" 🗣️ GESTOR DE COMPRAS (Escribe 'salir' para terminar)")
print("="*50)

while True:
    frase = input("\nTú: ")
    if frase.lower() in ['salir', 'exit', 'quit']: break

    intent, item, quantity, reply = cerebro_nlp.parse_intent(frase)
    print(f" 🤖 [Intent: {intent} | Item: {item} | Cantidad: {quantity}]")

    # --- LÓGICA DEL PLANNER ---
    
    # 1. AÑADIR A LA LISTA
    if intent == "add" and item:
        mi_lista[item] = mi_lista.get(item, 0) + quantity
        print(f" 📋 Cart-ON: ¡Anotado! He añadido {quantity} de {item} a tu lista.")

    # 2. BORRAR DE LA LISTA
    elif intent == "delete" and item:
        if item in mi_lista:
            del mi_lista[item]
            print(f" 📋 Cart-ON: He borrado '{item}' de tu lista de la compra.")
        else:
            print(f" 📋 Cart-ON: '{item}' no estaba en tu lista.")

    # 3. VACIAR LISTA
    elif intent == "clear":
        mi_lista.clear()
        print(" 📋 Cart-ON: He vaciado toda tu lista de la compra. ¡Empezamos de cero!")

    # 4. LEER QUÉ HAY EN LA LISTA
    elif intent == "read_list":
        if not mi_lista:
            print(" 📋 Cart-ON: Ahora mismo tu lista está vacía.")
        else:
            print(" 📋 Cart-ON: En tu lista tienes:")
            for prod, cant in mi_lista.items():
                print(f"    - {cant}x {prod}")

    # 5. COMPROBAR DISPONIBILIDAD (Cruzar Lista con BBDD)
    elif intent == "check_availability":
        if not mi_lista:
            print(" 🔍 Cart-ON: Tu lista está vacía, no hay nada que comprobar.")
        else:
            print(" 🔍 Cart-ON: Voy a comprobar el almacén...")
            for prod, cant_requerida in mi_lista.items():
                cursor.execute("SELECT nombre_pantalla, stock_actual FROM productos WHERE sinonimos LIKE %s OR nombre_pantalla LIKE %s", (f"%{prod.lower()}%", f"%{prod.lower()}%"))
                resultados = cursor.fetchall()
                
                if resultados:
                    stock_real = resultados[0]['stock_actual']
                    nombre_real = resultados[0]['nombre_pantalla']
                    if stock_real >= cant_requerida:
                        print(f"    ✅ Hay stock suficiente de {nombre_real} (Tienes {cant_requerida} en lista y hay {stock_real} en tienda).")
                    elif stock_real > 0:
                        print(f"    ⚠️ Cuidado: Solo quedan {stock_real} de {nombre_real}, pero tú querías {cant_requerida}.")
                    else:
                        print(f"    ❌ Nos hemos quedado sin {nombre_real} (Stock: 0).")
                else:
                    print(f"    ❓ El producto '{prod}' no existe en nuestro catálogo del supermercado.")

    # 6. LEER STOCK DE UN SOLO PRODUCTO
    elif intent == "read_stock" and item:
        cursor.execute("SELECT nombre_pantalla, stock_actual FROM productos WHERE sinonimos LIKE %s OR nombre_pantalla LIKE %s", (f"%{item.lower()}%", f"%{item.lower()}%"))
        res = cursor.fetchall()
        if res: print(f" 🛒 Cart-ON: Quedan {res[0]['stock_actual']} uds de {res[0]['nombre_pantalla']}.")
        else: print(f" ❓ Cart-ON: No encuentro '{item}' en la tienda.")

    elif intent == "chat" and reply: print(f" 🤖 Cart-ON: {reply}")
    else: print(" 🤖 Cart-ON: Mmm, no estoy seguro de qué hacer con eso.")

cursor.close()
conexion_db.close()