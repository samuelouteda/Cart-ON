import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class SQLManager:
    def __init__(self):
        print("[SQLManager] Gestor de Base de Datos Universal Dual Inicializado.")

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
            print(f"[SQLManager] Error conectando a MySQL: {e}")
            return None

    # ==========================================
    # MODO SUPERMERCADO
    # ==========================================
    def get_product_info(self, item_name: str):
        """Busca el producto en la BD usando búsqueda aproximada."""
        if not item_name or item_name == "producto desconocido":
            return None
            
        termino = item_name.lower().strip()
        conn = self.get_connection()
        if not conn: return None

        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT nombre_pantalla, precio, stock_actual 
                FROM productos 
                WHERE LOWER(nombre_yolo) LIKE %s OR LOWER(nombre_pantalla) LIKE %s
            """
            cursor.execute(query, (f"%{termino}%", f"%{termino}%"))
            resultado = cursor.fetchone()
            return resultado
        except Exception as e:
            print(f"Error buscando el producto en SQL: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    # ==========================================
    # MODO ESCUELA: UBICACIÓN DIRECTA (ESTRICTA DE SM)
    # ==========================================
    def get_classroom_location(self, nombre_aula: str):
        """Devuelve las coordenadas exactas de un aula evitando subcoincidencias locas."""
        conn = self.get_connection()
        if not conn: return None
        
        # Convierte espacios de voz en "%" para encajar "Q4 1005" con "Q4/1005" en MySQL.
        # Quitamos los comodines exteriores para que "Q4" no se líe con "Q4/1005".
        aula_limpia = nombre_aula.strip().replace(" ", "%")
        
        try:
            cursor = conn.cursor(dictionary=True) 
            query = "SELECT latitud, longitud FROM aulas_uab WHERE nombre_aula LIKE %s"
            cursor.execute(query, (aula_limpia,))
            resultado = cursor.fetchone()
            return resultado
        except Exception as e:
            print(f"Error buscando el aula en SQL: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    # ==========================================
    # MODO ESCUELA: HORARIO + COORDENADAS (ALGORITMO RAÍZ MULTILINGÜE)
    # ==========================================
    def get_school_info(self, asignatura: str = None, grupo: str = None, hora: str = None):
        """Busca la clase y hace JOIN cruzando la raíz de la asignatura (ES/CAT)."""
        conn = self.get_connection()
        if not conn: return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT h.*, a.latitud, a.longitud 
                FROM horarios_uab h
                LEFT JOIN aulas_uab a ON h.aula = a.nombre_aula
                WHERE 1=1
            """
            params = []
            
            # Algoritmo de filtrado de SM por la palabra más larga y truncado de sufijos a 6 caracteres
            if asignatura and asignatura != "producto desconocido":
                asignatura_limpia = asignatura.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                asignatura_limpia = asignatura_limpia.replace('à','a').replace('è','e').replace('ò','o')
                
                palabras = asignatura_limpia.split()
                palabras_clave = [p for p in palabras if len(p) > 3 and p not in ["para", "como", "pero", "clase", "aula"]]
                
                if palabras_clave:
                    palabra_principal = max(palabras_clave, key=len)
                    raiz = palabra_principal[:6]  # Asegura 'multim', 'comput', 'arquac', 'infaes'
                    
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
            print(f"[SQLManager] Error consultando asignaturas UAB: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()