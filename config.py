import pymysql
from flask import Flask

app = Flask(__name__)
app.secret_key = 'gestion_umb_sesiones_secret_key_2026'

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'gestion_umb_sesiones',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def conectar_db():
    """Establece y retorna una conexión a la base de datos"""
    try:
        conexion = pymysql.connect(**DB_CONFIG)
        print("Conexión exitosa a la base de datos")
        return conexion
    except pymysql.MySQLError as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None