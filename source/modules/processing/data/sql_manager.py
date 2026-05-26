import mysql.connector
import os

class CloudSQLManager:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        
        # Al iniciar, comprobamos y preparamos la base de datos automáticamente
        self.setup_database()

    def _get_connection(self):
        """Establece la conexión con Google Cloud SQL."""
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                connect_timeout=5
            )
        except mysql.connector.Error as err:
            print(f"[CloudSQL] Error crítico de conexión: {err}")
            return None

    def setup_database(self):
        """Crea la tabla y mete datos de prueba si está vacía."""
        query_tabla = """
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre_yolo VARCHAR(50) NOT NULL UNIQUE,
                nombre_pantalla VARCHAR(100) NOT NULL,
                sinonimos TEXT,
                coordenada_x FLOAT DEFAULT NULL,
                coordenada_y FLOAT DEFAULT NULL,
                pasillo VARCHAR(20) DEFAULT NULL,
                stock_actual INT DEFAULT 0   -- ¡La columna de inventario añadida desde el inicio!
            );
        """
        query_datos = """
            INSERT IGNORE INTO productos (nombre_yolo, nombre_pantalla, sinonimos, coordenada_x, coordenada_y, pasillo, stock_actual) 
            VALUES 
            ('milk_carton', 'Leche Entera', 'leche,lacteo,carton', 14.5, 32.2, 'Pasillo 4', 0),
            ('pasta_reggia', 'Macarrones 500g', 'pasta,macarrones,espaguetis', 8.1, 12.4, 'Pasillo 3', 0);
        """
        conexion = self._get_connection()
        if conexion:
            cursor = conexion.cursor()
            try:
                cursor.execute(query_tabla)
                cursor.execute(query_datos)
                conexion.commit()
                print("[CloudSQL] Base de datos verificada y lista con soporte de stock.")
            except Exception as e:
                print(f"[CloudSQL] Error en setup: {e}")
            finally:
                cursor.close()
                conexion.close()
        """Crea la tabla y mete datos de prueba si está vacía."""
        query_tabla = """
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre_yolo VARCHAR(50) NOT NULL UNIQUE,
                nombre_pantalla VARCHAR(100) NOT NULL,
                sinonimos TEXT,
                coordenada_x FLOAT DEFAULT NULL,
                coordenada_y FLOAT DEFAULT NULL,
                pasillo VARCHAR(20) DEFAULT NULL
            );
        """
        query_datos = """
            INSERT IGNORE INTO productos (nombre_yolo, nombre_pantalla, sinonimos, coordenada_x, coordenada_y, pasillo) 
            VALUES 
            ('milk_carton', 'Leche Entera', 'leche,lacteo,carton', 14.5, 32.2, 'Pasillo 4'),
            ('pasta_reggia', 'Macarrones 500g', 'pasta,macarrones,espaguetis', 8.1, 12.4, 'Pasillo 3');
        """
        conexion = self._get_connection()
        if conexion:
            cursor = conexion.cursor()
            try:
                cursor.execute(query_tabla)
                cursor.execute(query_datos)
                conexion.commit()
                print("[CloudSQL] Base de datos verificada y lista.")
            except Exception as e:
                print(f"[CloudSQL] Error en setup: {e}")
            finally:
                cursor.close()
                conexion.close()

    def buscar_producto(self, termino):
        """Busca un producto por coincidencia en sus sinónimos."""
        if not termino: return None
        
        query = """
            SELECT coordenada_x, coordenada_y, nombre_pantalla, pasillo 
            FROM productos 
            WHERE sinonimos LIKE %s OR nombre_pantalla LIKE %s
            LIMIT 1
        """
        conexion = self._get_connection()
        if conexion:
            cursor = conexion.cursor(dictionary=True)
            try:
                busqueda = f"%{termino.lower()}%"
                cursor.execute(query, (busqueda, busqueda))
                resultado = cursor.fetchone()
                return resultado
            except Exception as e:
                print(f"[CloudSQL] Error buscando '{termino}': {e}")
            finally:
                cursor.close()
                conexion.close()
        return None