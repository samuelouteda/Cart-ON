import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class SQLManager:
    def __init__(self):
        print("[SQLManager] Gestor de Base de Datos inicializado y fusionado.")

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
            print(f"Error buscando el producto en SQL: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
   # ==========================================
    # MODO ESCUELA: UBICACIÓN DIRECTA (ESTRICTA)
    # ==========================================
    def get_classroom_location(self, nombre_aula: str):
        """Devuelve las coordenadas exactas de un aula para generar el QR."""
        conn = self.get_connection()
        if not conn: return None
        
        aula_limpia = nombre_aula.strip().replace(" ", "%")
        
        try:
            cursor = conn.cursor(dictionary=True) 
            # FÍJATE: Hemos quitado los f"%{...}%" para que no se invente finales ni principios
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
    # MODO ESCUELA: HORARIO + COORDENADAS
    # ==========================================
    def get_school_info(self, asignatura: str = None, grupo: str = None, hora: str = None):
        """Busca la clase y hace JOIN para llevarse también la ubicación del aula para el mapa visual."""
        conn = self.get_connection()
        if not conn: return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # JOIN entre horarios y aulas
            query = """
                SELECT h.*, a.latitud, a.longitud 
                FROM horarios_uab h
                LEFT JOIN aulas_uab a ON h.aula = a.nombre_aula
                WHERE 1=1
            """
            params = []
            
            # Lógica de búsqueda flexible (Anti-fallos Español/Catalán)
            if asignatura and asignatura != "producto desconocido":
                # 1. Limpiamos acentos de la petición
                asignatura_limpia = asignatura.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                asignatura_limpia = asignatura_limpia.replace('à','a').replace('è','e').replace('ò','o')
                
                palabras = asignatura_limpia.split()
                # 2. Filtramos palabras cortas o artículos
                palabras_clave = [p for p in palabras if len(p) > 3 and p not in ["para", "como", "pero"]]
                
                if palabras_clave:
                    # 3. TRUCO: Cogemos la palabra más larga (ej: 'multimedia', 'computador')
                    palabra_principal = max(palabras_clave, key=len)
                    # 4. Cogemos las primeras 6 letras para evitar fallos de sufijos ES/CAT
                    raiz = palabra_principal[:6] 
                    
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
            print(f"[SQLManager] Error consultando UAB: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()