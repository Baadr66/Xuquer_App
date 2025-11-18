import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    # Base de datos
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # Email
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    @staticmethod
    def validate():
        """Valida que todas las variables críticas estén configuradas"""
        required_vars = [
            'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
            'MAIL_USERNAME', 'MAIL_PASSWORD', 'SECRET_KEY'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"❌ Faltan variables de entorno: {', '.join(missing)}")
        
        print("✅ Configuración validada correctamente")