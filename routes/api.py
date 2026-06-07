from flask import Blueprint, request, jsonify, session
import config
from routes.helpers import enviar_credenciales_usuario
from werkzeug.security import generate_password_hash

api_bp = Blueprint('api', __name__, url_prefix='/api')

# ==================== TIPOS, ESCENARIOS, CARRERAS ====================
@api_bp.route('/tipos-sesion')
def api_tipos_sesion():
    conexion = config.conectar_db()
    if not conexion:
        return jsonify([])
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_tipo_sesion, nombre_sesion FROM tipo_sesion")
            return jsonify(cursor.fetchall())
    finally:
        conexion.close()

@api_bp.route('/escenarios')
def api_escenarios():
    conexion = config.conectar_db()
    if not conexion:
        return jsonify([])
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_escenario, nombre_escenario FROM escenarios")
            return jsonify(cursor.fetchall())
    finally:
        conexion.close()

@api_bp.route('/carreras')
def api_carreras():
    conexion = config.conectar_db()
    if not conexion:
        return jsonify([])
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            return jsonify(cursor.fetchall())
    finally:
        conexion.close()

# ==================== SESIONES API ====================
@api_bp.route('/sesiones')
def api_sesiones():
    if not session.get('admin_logged'):
        return jsonify([])
    
    conexion = config.conectar_db()
    if not conexion:
        return jsonify([])
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT s.*, ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre, c.nombre_carrera as carrera_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                LEFT JOIN carreras c ON s.id_carrera = c.id_carrera
                ORDER BY s.fecha DESC, s.hora_inicio ASC
            """)
            sesiones = cursor.fetchall()
            
            resultado = []
            for sesion in sesiones:
                item = dict(sesion)
                if item.get('fecha'):
                    item['fecha_str'] = item['fecha'].strftime('%d/%m/%Y')
                    item['fecha'] = item['fecha'].strftime('%Y-%m-%d')
                
                for campo in ('hora_inicio', 'hora_fin'):
                    val = item.get(campo)
                    if val:
                        if hasattr(val, 'seconds'):
                            total_seconds = val.seconds
                            hours = total_seconds // 3600
                            minutes = (total_seconds % 3600) // 60
                            item[campo] = f"{hours:02d}:{minutes:02d}"
                        elif hasattr(val, 'strftime'):
                            item[campo] = val.strftime('%H:%M')
                        else:
                            item[campo] = str(val)[:5] if val else None
                
                resultado.append(item)
            
            return jsonify(resultado)
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify([])
    finally:
        conexion.close()

# ==================== USUARIOS API ====================
@api_bp.route('/usuarios', methods=['POST'])
def api_crear_usuario():
    if not session.get('admin_logged'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    data = request.get_json()
    rol = data.get('rol')
    nombre = data.get('nombre')
    apellido_paterno = data.get('apellido_paterno')
    apellido_materno = data.get('apellido_materno', '')
    correo = data.get('correo')
    
    if not nombre or not apellido_paterno or not correo:
        return jsonify({'success': False, 'message': 'Faltan campos'})
    
    nombre_completo = f"{nombre} {apellido_paterno} {apellido_materno}".strip()
    conexion = config.conectar_db()
    
    try:
        if rol == 'alumno':
            matricula = data.get('matricula')
            id_carrera = data.get('id_carrera')
            if not matricula:
                return jsonify({'success': False, 'message': 'Matrícula requerida'})
            
            password_temporal = matricula
            hashed = generate_password_hash(password_temporal)
            
            with conexion.cursor() as cursor:
                cursor.execute("INSERT INTO alumnos (nombre_alumno, apellido_paterno, apellido_materno, correo_electronico, matricula, password, id_carrera, primer_login) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)",
                              (nombre, apellido_paterno, apellido_materno, correo, matricula, hashed, id_carrera))
                conexion.commit()
            
            enviar_credenciales_usuario(nombre_completo, correo, password_temporal, 'alumno')
            return jsonify({'success': True, 'message': 'Alumno creado'})
        
        elif rol == 'admin':
            password_temporal = 'Admin123'
            hashed = generate_password_hash(password_temporal)
            
            with conexion.cursor() as cursor:
                cursor.execute("INSERT INTO administrador (nombre_admin, apellido_paterno, apellido_materno, email, password, primer_login) VALUES (%s, %s, %s, %s, %s, TRUE)",
                              (nombre, apellido_paterno, apellido_materno, correo, hashed))
                conexion.commit()
            
            enviar_credenciales_usuario(nombre_completo, correo, password_temporal, 'admin')
            return jsonify({'success': True, 'message': 'Administrador creado'})
        
        else:
            return jsonify({'success': False, 'message': 'Rol no válido'})
    except Exception as e:
        conexion.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conexion.close()

@api_bp.route('/usuarios', methods=['GET'])
def api_usuarios():
    if not session.get('admin_logged'):
        return jsonify({'error': 'No autorizado'}), 401
    
    conexion = config.conectar_db()
    usuarios = []
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT a.id_alumno as id, a.nombre_alumno as nombre, a.apellido_paterno, a.apellido_materno, a.correo_electronico as correo, a.matricula, a.id_carrera, a.primer_login, c.nombre_carrera, 'alumno' as rol FROM alumnos a LEFT JOIN carreras c ON a.id_carrera = c.id_carrera ORDER BY a.id_alumno DESC")
            for alumno in cursor.fetchall():
                usuarios.append(dict(alumno))
            
            cursor.execute("SELECT id_control as id, nombre_admin as nombre, apellido_paterno, apellido_materno, email as correo, primer_login, 'admin' as rol FROM administrador ORDER BY id_control DESC")
            for admin in cursor.fetchall():
                usuarios.append(dict(admin))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conexion.close()
    
    return jsonify(usuarios)

@api_bp.route('/usuarios/<int:id>', methods=['GET'])
def api_usuario_by_id(id):
    if not session.get('admin_logged'):
        return jsonify({'error': 'No autorizado'}), 401
    
    rol = request.args.get('rol')
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            if rol == 'alumno':
                cursor.execute("SELECT a.id_alumno as id, a.nombre_alumno as nombre, a.apellido_paterno, a.apellido_materno, a.correo_electronico as correo, a.matricula, a.id_carrera, a.primer_login, c.nombre_carrera, 'alumno' as rol FROM alumnos a LEFT JOIN carreras c ON a.id_carrera = c.id_carrera WHERE a.id_alumno = %s", (id,))
            else:
                cursor.execute("SELECT id_control as id, nombre_admin as nombre, apellido_paterno, apellido_materno, email as correo, primer_login, 'admin' as rol FROM administrador WHERE id_control = %s", (id,))
            
            usuario = cursor.fetchone()
            if not usuario:
                return jsonify({'error': 'Usuario no encontrado'}), 404
            return jsonify(dict(usuario))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conexion.close()

@api_bp.route('/usuarios/<int:id>', methods=['PUT'])
def api_actualizar_usuario(id):
    if not session.get('admin_logged'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    data = request.get_json()
    rol = data.get('rol')
    nombre = data.get('nombre')
    apellido_paterno = data.get('apellido_paterno')
    apellido_materno = data.get('apellido_materno', '')
    correo = data.get('correo')
    
    conexion = config.conectar_db()
    
    try:
        if rol == 'alumno':
            matricula = data.get('matricula')
            id_carrera = data.get('id_carrera')
            with conexion.cursor() as cursor:
                cursor.execute("UPDATE alumnos SET nombre_alumno=%s, apellido_paterno=%s, apellido_materno=%s, correo_electronico=%s, matricula=%s, id_carrera=%s WHERE id_alumno=%s",
                              (nombre, apellido_paterno, apellido_materno, correo, matricula, id_carrera, id))
        else:
            with conexion.cursor() as cursor:
                cursor.execute("UPDATE administrador SET nombre_admin=%s, apellido_paterno=%s, apellido_materno=%s, email=%s WHERE id_control=%s",
                              (nombre, apellido_paterno, apellido_materno, correo, id))
        conexion.commit()
        return jsonify({'success': True, 'message': 'Usuario actualizado'})
    except Exception as e:
        conexion.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conexion.close()

@api_bp.route('/usuarios/<int:id>', methods=['DELETE'])
def api_eliminar_usuario(id):
    if not session.get('admin_logged'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    rol = request.args.get('rol')
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            if rol == 'alumno':
                cursor.execute("DELETE FROM alumnos WHERE id_alumno = %s", (id,))
            else:
                cursor.execute("DELETE FROM administrador WHERE id_control = %s", (id,))
        conexion.commit()
        return jsonify({'success': True, 'message': 'Usuario eliminado'})
    except Exception as e:
        conexion.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conexion.close()