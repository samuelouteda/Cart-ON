import os
from dotenv import load_dotenv

# Carga las variables desde un archivo .env si estamos probando en local
# En Google Cloud Run, cogerá directamente las variables de entorno de la consola de Google.
load_dotenv()

class Config:
    """
    Gestor Central de Configuración y Secretos.
    Ningún otro archivo debe usar os.getenv() directamente, todos le preguntan a esta clase.
    """
    
    # Tokens de Inteligencia Artificial (UAB)
    UAB_TOKEN = os.getenv("UAB_TOKEN", "accesoAlLLM")
    UAB_BASE_URL = os.getenv("UAB_BASE_URL", "https://dcc-llm.uab.cat/bes2/v1")
    
    # Configuración de Base de Datos (Cloud SQL)
    # Las contraseñas por defecto deben estar vacías o ser falsas
    DB_USER = os.getenv("DB_USER", "usuario_local")
    DB_PASS = os.getenv("DB_PASS", "") 
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "carton_db")
    
    # Otras configuraciones del servidor
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    @classmethod
    def get_db_connection_string(cls):
        # Ejemplo para SQLAlchemy o Psycopg2
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASS}@{cls.DB_HOST}/{cls.DB_NAME}"