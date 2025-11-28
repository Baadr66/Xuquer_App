import psycopg2
from config import Config
# Conexión a la base de datos PostgreSQL
try:

    database = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )
    
    print("✅ Conexión a la base de datos exitosa")

except psycopg2.Error as e:
    print("❌ Error al conectar con la base de datos:")
    print(e)
    database = None  # para evitar que falle si no se conecta


class Email:
    def __init__(self):
        self.database = database  # Usa la conexión global
    
    def listarusers(self):
        if self.database:
            try:
                cursor = self.database.cursor()
                cursor.execute("SELECT email FROM usuarios ORDER BY email ASC")
                resultados = cursor.fetchall()
                cursor.close()
                print("Usuarios listados correctamente")
                return [row[0] for row in resultados]
            except psycopg2.Error as ex:
                print(f"Error al listar usuarios: {ex}")
                return []
        else:
            print("No hay conexión a la base de datos")
            return []
