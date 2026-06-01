import mysql.connector
from mysql.connector import Error

class SQLManager:
    """
    Gestor de Base de Datos para Google Cloud SQL.
    Su única responsabilidad es hacer consultas (queries) y devolver diccionarios.
    No sabe nada de Gemini, ni de la UAB, ni del hardware físico.
    """
    def __init__(self):
        # ⚠️ Nota del Tech Lead: En un futuro, esto debería leerse de variables de entorno (.env)
        # por seguridad, pero para la demo lo dejamos fijo.
        self.config = {
            "host": "34.28.135.54",
            "user": "marco-mejias",
            "password": "cart-on-Fortnite67",
            "database": "carton_db"
        }
        print("[SQLManager] 🗄️ Módulo de base de datos inicializado.")

    def _get_connection(self):
        """Abre una conexión fresca. Crucial para Cloud Run."""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            print(f"[SQLManager] 🔴 Error conectando a Google Cloud SQL: {e}")
            return None

    # ==========================================
    # 🛒 CONSULTAS: FASE DE INTERACCIÓN / ASISTENCIA
    # ==========================================

    def get_product_info(self, item_name):
        """
        Busca un producto por nombre o sinónimo.
        Devuelve un diccionario con sus datos o None si no existe.
        """
        if not item_name or item_name in ["desconocido", "black"]:
            return None
            
        conexion = self._get_connection()
        if not conexion:
            return None
            
        try:
            cursor = conexion.cursor(dictionary=True)
            query = """
                SELECT nombre_pantalla, stock_actual, precio 
                FROM productos 
                WHERE sinonimos LIKE %s OR nombre_pantalla LIKE %s 
                LIMIT 1
            """
            # Los %s protegen contra inyecciones SQL
            cursor.execute(query, (f"%{item_name}%", f"%{item_name}%"))
            resultado = cursor.fetchone()
            return resultado
            
        except Error as e:
            print(f"[SQLManager] 🔴 Error buscando producto '{item_name}': {e}")
            return None
            
        finally:
            # 🧹 Limpieza obligatoria para que Cloud Run no se sature
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()

    # ==========================================
    # 🗺️ CONSULTAS: FASE DE ESCANEO (SLAM)
    # ==========================================

    def update_product_location(self, item_name, pos_x, pos_y):
        """
        Actualiza las coordenadas X,Y de un producto cuando el robot
        lo detecta durante la ronda de mapeo nocturno.
        """
        conexion = self._get_connection()
        if not conexion:
            return False
            
        try:
            cursor = conexion.cursor()
            query = """
                UPDATE productos 
                SET coord_x = %s, coord_y = %s 
                WHERE nombre_pantalla = %s OR sinonimos LIKE %s
            """
            cursor.execute(query, (pos_x, pos_y, item_name, f"%{item_name}%"))
            conexion.commit() # Guardamos los cambios
            return cursor.rowcount > 0 # Devuelve True si actualizó algo
            
        except Error as e:
            print(f"[SQLManager] 🔴 Error actualizando coordenadas: {e}")
            return False
            
        finally:
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()

    # ==========================================
    # 📋 CONSULTAS: LISTA DE LA COMPRA (FUTURO)
    # ==========================================
    
    # Aquí iremos metiendo las funciones de add_to_list, remove_from_list, etc.
    # a medida que las vayas necesitando.