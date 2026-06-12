import os
import pymysql
from flask import Flask
from dotenv import load_dotenv

# Cargar variables del archivo .env (solo para desarrollo local)
load_dotenv()

app = Flask(__name__)

# Clave secreta - primero intentar desde .env, si no usar la del código
app.secret_key = os.environ.get('SECRET_KEY', 'gestion_umb_sesiones_secret_key_2026')

# ==================== CONFIGURACIÓN DINÁMICA DE URL BASE ====================
# Detectar si estamos en Railway automáticamente
if os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
    BASE_URL = f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}"
else:
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

print(f"🔗 URL BASE configurada: {BASE_URL}")  # Para depuración

# ==================== CONFIGURACIÓN DE BASE DE DATOS ====================
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'gestion_umb_sesiones'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# ==================== CONFIGURACIÓN DE CORREO ====================
# Configuración para Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', '')

# ==================== FUNCIÓN DE CONEXIÓN ====================
def conectar_db():
    """Establece y retorna una conexión a la base de datos"""
    try:
        conexion = pymysql.connect(**DB_CONFIG)
        print("✅ Conexión exitosa a la base de datos")
        return conexion
    except pymysql.MySQLError as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        return None