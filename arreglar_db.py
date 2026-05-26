import mysql.connector

try:
    print("Conectando a la base de datos como root...")
    # Pon aquí tu IP pública y la contraseña que le pusiste a root
    conexion = mysql.connector.connect(
        host="34.28.135.54", 
        user="root",
        password="cart-on-Fortnite67",
        database="carton_db"
    )
    
    cursor = conexion.cursor()
    
    print("Inyectando nueva columna de stock...")
    cursor.execute("ALTER TABLE productos ADD COLUMN stock_actual INT DEFAULT 0;")
    conexion.commit()
    
    print("¡ÉXITO! Columna 'stock_actual' añadida correctamente.")
    
except mysql.connector.Error as err:
    # Si da error 1060 es que la columna ya existía, ¡así que perfecto!
    if err.errno == 1060:
        print("¡TODO LISTO! La columna 'stock_actual' ya estaba creada.")
    else:
        print(f"Error: {err}")
finally:
    if 'cursor' in locals(): cursor.close()
    if 'conexion' in locals(): conexion.close()