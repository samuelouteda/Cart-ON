# db/sql_manager.py
# (Asegúrate de importar tu librería de conexión real: psycopg2, pymysql o sqlalchemy)

class SQLManager:
    def __init__(self):
        print("[SQLManager] 🗄️ Gestor de Base de Datos inicializado.")
        # Aquí inicializarías tu conexión real a Google Cloud SQL

    def get_product_info(self, item_name: str):
        """
        Búsqueda difusa (Fuzzy Search). 
        Encuentra 'Plátano de Canarias' aunque busques 'platano'.
        """
        if not item_name:
            return None
            
        # 1. Aseguramos que el término esté en minúsculas para comparar
        termino = item_name.lower()
        
        # ⚠️ AQUÍ VA TU LÓGICA SQL REAL. El concepto es usar LIKE con %:
        # QUERY: SELECT * FROM productos WHERE LOWER(nombre_pantalla) LIKE '%platano%' OR LOWER(nombre_yolo) LIKE '%platano%'
        
        # --- SIMULACIÓN BASADA EN TU CAPTURA DE PANTALLA ---
        simulacion_bd = [
            {"nombre_yolo": "apple", "nombre_pantalla": "Manzana Fuji Premium", "precio": 1.89, "stock_actual": 20},
            {"nombre_yolo": "banana", "nombre_pantalla": "Plátano de Canarias", "precio": 2.15, "stock_actual": 15},
            {"nombre_yolo": "bottle", "nombre_pantalla": "Botella de Agua Bezoya 1L", "precio": 0.85, "stock_actual": 30},
            {"nombre_yolo": "tomato", "nombre_pantalla": "Tomate Pera", "precio": 1.20, "stock_actual": 50}
        ]
        
        # Buscamos si la palabra raíz está dentro de nombre_yolo o nombre_pantalla
        for producto in simulacion_bd:
            # Quitamos tildes rápido para comparar de forma segura
            nombre_limpio = producto["nombre_pantalla"].lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            
            if termino in nombre_limpio or termino in producto["nombre_yolo"].lower():
                return producto
                
        return None
    
    def get_classroom_location(self, nombre_aula):
        query = "SELECT latitud, longitud FROM aulas_uab WHERE nombre_aula LIKE %s"
        # Usamos LIKE con % para que si el usuario dice "Q300", encuentre "Q3/000" si es similar (ajusta según tu BD)
        self.cursor.execute(query, (f"%{nombre_aula}%",))
        return self.cursor.fetchone()
    
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
                # Rompemos la asignatura en palabras (ej. "vision", "computador")
                palabras = asignatura.lower().split()
                # Quitamos palabras comunes que no aportan (stop words)
                palabras_clave = [p for p in palabras if p not in ["de", "por", "para", "la", "el", "los", "las"]]
                
                # Construimos un filtro flexible: debe coincidir AL MENOS UNA palabra clave principal
                # Usamos la primera palabra importante (ej. "vision")
                if palabras_clave:
                    raiz = palabras_clave[0]
                    # Quitamos acentos de la búsqueda
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