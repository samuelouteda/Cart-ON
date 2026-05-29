import mysql.connector

class RobotHRIBase:
    """Clase base para la interacción Humano-Robot de Cart-ON"""
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.cursor = None

    def conectar_bd(self):
        try:
            self.conn = mysql.connector.connect(**self.db_config)
            self.cursor = self.conn.cursor(dictionary=True)
        except mysql.connector.Error as err:
            print(f"❌ Error de conexión a la BBDD: {err}")

    def desconectar_bd(self):
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()


class SupermercadoHRI(RobotHRIBase):
    """Perfil de Cart-ON para el Modo Supermercado (Visión con YOLO)"""
    def procesar_peticion(self, nombre_producto_yolo):
        self.conectar_bd()
        
        query = "SELECT nombre_pantalla, precio, stock_actual FROM productos WHERE nombre_yolo = %s"
        self.cursor.execute(query, (nombre_producto_yolo,))
        producto = self.cursor.fetchone()
        
        self.desconectar_bd()
        
        if producto:
            if producto['stock_actual'] > 0:
                return f"He detectado {producto['nombre_pantalla']}. Cuesta {producto['precio']}€ y quedan {producto['stock_actual']} en stock."
            else:
                return f"He detectado {producto['nombre_pantalla']}, pero el stock está agotado."
        
        return f"He detectado '{nombre_producto_yolo}', pero no está en la base de datos."