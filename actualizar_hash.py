from werkzeug.security import generate_password_hash
import pymysql
import config

conexion = config.conectar_db()
cursor = conexion.cursor()

nuevo_hash = generate_password_hash('130000')
print(f"Hash para '130000': {nuevo_hash}")

cursor.execute("UPDATE administrador SET password = %s WHERE id_control = 1", (nuevo_hash,))
conexion.commit()

print("✅ Contraseña actualizada")
cursor.close()
conexion.close()