import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class SQLManager:
    def __init__(self):
        print("[SQLManager] 🗄️ Gestor de Base de Datos inicializado.")

    def get_connection(self):
        """Crea y devuelve una nueva conexión a la base de datos."""
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "marco-mejias"),
                password=os.getenv("DB_PASSWORD", "cart-on-Fortnite67"),
                database=os.getenv("DB_NAME", "carton_db") # ⚠️ 
            )
            return conn
        except Exception as e:
            print(f"[SQLManager] 🔴 Error conectando a MySQL: {e}")
            return None

    def get_product_info(self, item_name: str):
        """
        Búsqueda difusa (Fuzzy Search). 
        Encuentra 'Plátano de Canarias' aunque busques 'platano'.
        """
        if not item_name:
            return None
            
        termino = item_name.lower()
        
        # --- SIMULACIÓN BASADA EN TU CAPTURA DE PANTALLA ---
        simulacion_bd = [
            {"nombre_yolo": "apple", "nombre_pantalla": "Manzana Fuji Premium", "precio": 1.89, "stock_actual": 20},
            {"nombre_yolo": "banana", "nombre_pantalla": "Plátano de Canarias", "precio": 2.15, "stock_actual": 15},
            {"nombre_yolo": "bottle", "nombre_pantalla": "Botella de Agua Bezoya 1L", "precio": 0.85, "stock_actual": 30},
            {"nombre_yolo": "tomato", "nombre_pantalla": "Tomate Pera", "precio": 1.20, "stock_actual": 50}
        ]
        
        for producto in simulacion_bd:
            nombre_limpio = producto["nombre_pantalla"].lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            if termino in nombre_limpio or termino in producto["nombre_yolo"].lower():
                return producto
                
        return None
    
    def get_classroom_location(self, nombre_aula):
        try:
            conn = self.get_connection()
            if not conn: return None
            
            cursor = conn.cursor(dictionary=True) 
            query = "SELECT latitud, longitud FROM aulas_uab WHERE nombre_aula LIKE %s"
            cursor.execute(query, (f"%{nombre_aula}%",))
            resultado = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"🔴 Error buscando el aula en SQL: {e}")
            return None
    
    def get_school_info(self, asignatura: str = None, grupo: str = None, hora: str = None):
        try:
            conn = self.get_connection()
            if not conn: return []
            
            cursor = conn.cursor(dictionary=True)
            
            # Juntamos la tabla de horarios con la de aulas usando el nombre del aula
            query = """
                SELECT h.*, a.latitud, a.longitud 
                FROM horarios_uab h
                LEFT JOIN aulas_uab a ON h.aula = a.nombre_aula
                WHERE 1=1
            """
            params = []
            
            if asignatura and asignatura != "producto desconocido":
                palabras = asignatura.lower().split()
                palabras_clave = [p for p in palabras if p not in ["de", "por", "para", "la", "el", "los", "las"]]
                
                if palabras_clave:
                    raiz = palabras_clave[0]
                    raiz = raiz.replace('ó', 'o').replace('í', 'i')
                    query += " AND LOWER(asignatura) LIKE %s"
                    params.append(f"%{raiz}%")
                
            if grupo:
                query += " AND grupo = %s"
                params.append(grupo)
                
            if hora:
                query += " AND hora_inicio LIKE %s"
                params.append(f"{hora}%")
                
            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            
            cursor.close()
            conn.close()
            return resultados
        except Exception as e:
            print(f"[SQLManager] 🔴 Error consultando UAB: {e}")
            return []