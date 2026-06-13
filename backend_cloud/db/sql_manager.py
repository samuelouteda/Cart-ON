import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class SQLManager:
    def __init__(self):
        print("[SQLManager] 🗄️ Gestor de Base de Datos inicializado y fusionado.")

    def get_connection(self):
        """Crea y devuelve una nueva conexión limpia a la base de datos."""
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "34.28.135.54"),
                user=os.getenv("DB_USER", "marco-mejias"),
                password=os.getenv("DB_PASS", "cart-on-Fortnite67"),
                database=os.getenv("DB_NAME", "carton_db")
            )
            return conn
        except Exception as e:
            print(f"[SQLManager] 🔴 Error conectando a MySQL: {e}")
            return None

    # ==========================================
    # 🛒 MODO SUPERMERCADO (Ahora con BD Real)
    # ==========================================
    def get_product_info(self, item_name: str):
        """Busca el producto en la BD real usando búsqueda aproximada."""
        if not item_name or item_name == "producto desconocido":
            return None
            
        termino = item_name.lower().strip()
        conn = self.get_connection()
        if not conn: return None

        try:
            cursor = conn.cursor(dictionary=True)
            # Buscamos coincidencias tanto en el nombre interno como en el de pantalla
            query = """
                SELECT nombre_pantalla, precio, stock_actual 
                FROM productos 
                WHERE LOWER(nombre_yolo) LIKE %s OR LOWER(nombre_pantalla) LIKE %s
            """
            cursor.execute(query, (f"%{termino}%", f"%{termino}%"))
            resultado = cursor.fetchone()
            
            return resultado
        except Exception as e:
            print(f"🔴 Error buscando el producto en SQL: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    # ==========================================
    # 🛣️ MODO ESCUELA: UBICACIÓN DIRECTA
    # ==========================================
    def get_classroom_location(self, nombre_aula: str):
        """Devuelve las coordenadas exactas de un aula."""
        conn = self.get_connection()
        if not conn: return None
        
        try:
            cursor = conn.cursor(dictionary=True) 
            query = "SELECT latitud, longitud FROM aulas_uab WHERE nombre_aula LIKE %s"
            cursor.execute(query, (f"%{nombre_aula}%",))
            resultado = cursor.fetchone()
            
            return resultado
        except Exception as e:
            print(f"🔴 Error buscando el aula en SQL: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    # ==========================================
    # 🗓️ MODO ESCUELA: HORARIO + COORDENADAS
    # ==========================================
    def get_school_info(self, asignatura: str = None, grupo: str = None, hora: str = None):
        """Busca la clase y hace JOIN para llevarse también la ubicación del aula."""
        conn = self.get_connection()
        if not conn: return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 🚀 El JOIN mágico entre horarios y aulas
            query = """
                SELECT h.*, a.latitud, a.longitud 
                FROM horarios_uab h
                LEFT JOIN aulas_uab a ON h.aula = a.nombre_aula
                WHERE 1=1
            """
            params = []
            
            # 🔥 Tu lógica de limpieza de palabras clave (¡muy buena!)
            if asignatura and asignatura != "producto desconocido":
                palabras = asignatura.lower().split()
                palabras_clave = [p for p in palabras if p not in ["de", "por", "para", "la", "el", "los", "las"]]
                
                if palabras_clave:
                    raiz = palabras_clave[0]
                    raiz = raiz.replace('ó', 'o').replace('í', 'i')
                    query += " AND LOWER(h.asignatura) LIKE %s"
                    params.append(f"%{raiz}%")
                
            if grupo:
                query += " AND h.grupo = %s"
                params.append(grupo)
                
            if hora:
                query += " AND h.hora_inicio LIKE %s"
                params.append(f"{hora}%")
                
            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            
            return resultados
        except Exception as e:
            print(f"[SQLManager] 🔴 Error consultando UAB: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()