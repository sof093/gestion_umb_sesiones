from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
import os
import uuid
from datetime import datetime, date
from werkzeug.utils import secure_filename
import config
from routes.helpers import validar_solo_letras, validar_numero_positivo, validar_horas, validar_fecha_no_pasada, formatear_fecha, formatear_hora, convertir_hora_para_input

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Configuración de archivos
UPLOAD_FOLDER = 'static/uploads/sesiones'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== DASHBOARD ====================
@admin_bp.route('/dashboard')
def admin_dashboard():
    if not session.get('admin_logged'):
        flash('Debe iniciar sesión primero', 'warning')
        return redirect(url_for('auth.login'))
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM sesion")
            total_sesiones = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT ts.nombre_sesion, COUNT(s.id_sesion) as total 
                FROM tipo_sesion ts
                LEFT JOIN sesion s ON ts.id_tipo_sesion = s.id_tipo_sesion
                GROUP BY ts.id_tipo_sesion
            """)
            sesiones_por_tipo = cursor.fetchall()
            
            cursor.execute("""
                SELECT s.*, ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre,
                       c.nombre_carrera as carrera_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                LEFT JOIN carreras c ON s.id_carrera = c.id_carrera
                WHERE s.fecha >= CURDATE()
                ORDER BY s.fecha ASC, s.hora_inicio ASC
                LIMIT 5
            """)
            proximas_sesiones = cursor.fetchall()
            
    except Exception as e:
        print(f"Error en dashboard: {e}")
        total_sesiones = 0
        sesiones_por_tipo = []
        proximas_sesiones = []
    finally:
        conexion.close()
    
    return render_template('admin_dashboard.html', 
                         total_sesiones=total_sesiones,
                         sesiones_por_tipo=sesiones_por_tipo,
                         proximas_sesiones=proximas_sesiones)

# ==================== GESTIÓN DE SESIONES ====================
@admin_bp.route('/sesiones')
def admin_sesiones():
    if not session.get('admin_logged'):
        return redirect(url_for('auth.login'))
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT s.*, ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre,
                       c.nombre_carrera as carrera_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                LEFT JOIN carreras c ON s.id_carrera = c.id_carrera
                ORDER BY s.fecha DESC, s.hora_inicio ASC
            """)
            sesiones = cursor.fetchall()
    finally:
        conexion.close()
    
    return render_template('admin_sesiones.html', sesiones=sesiones)

@admin_bp.route('/sesion/nueva', methods=['GET', 'POST'])
def nueva_sesion():
    if not session.get('admin_logged'):
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        conexion = None
        try:
            sede = request.form.get('sede')
            nombre_de_sesion = request.form.get('nombre_de_sesion')
            fecha = request.form.get('fecha')
            nombre_ponente = request.form.get('nombre_ponente')
            apellido_paterno = request.form.get('apellido_paterno')
            apellido_materno = request.form.get('apellido_materno')
            perfil_profesional = request.form.get('perfil_profesional')
            biografia = request.form.get('biografia')
            id_tipo_sesion = request.form.get('id_tipo_sesion')
            hora_inicio = request.form.get('hora_inicio')
            hora_fin = request.form.get('hora_fin')
            cupo_audiencia = request.form.get('cupo_audiencia')
            id_carrera = request.form.get('id_carrera') or None
            id_escenario = request.form.get('id_escenario')
            id_evento = request.form.get('id_evento')
            tipo_procedencia = request.form.get('tipo_procedencia')
            nombre_institucion = None
            if tipo_procedencia == 'institucion':
                nombre_institucion = request.form.get('procedencia_institucion_independiente')
            
            if not all([sede, nombre_de_sesion, fecha, nombre_ponente, apellido_paterno, id_tipo_sesion, hora_inicio, hora_fin, id_escenario, id_evento]):
                return jsonify({'success': False, 'message': 'Todos los campos obligatorios deben ser llenados'}), 400
            
            if not validar_horas(hora_inicio, hora_fin):
                return jsonify({'success': False, 'message': 'La hora de fin debe ser posterior a la hora de inicio'}), 400
            
            conexion = config.conectar_db()
            if not conexion:
                return jsonify({'success': False, 'message': 'Error de conexión'}), 500
            
            # Validar disponibilidad del escenario
            with conexion.cursor() as cursor:
                sql_verificar = """
                    SELECT id_sesion, nombre_de_sesion, hora_inicio, hora_fin
                    FROM sesion 
                    WHERE id_escenario = %s AND fecha = %s
                    AND (
                        (hora_inicio < %s AND hora_fin > %s) OR
                        (hora_inicio BETWEEN %s AND %s) OR
                        (hora_fin BETWEEN %s AND %s) OR
                        (%s BETWEEN hora_inicio AND hora_fin)
                    )
                """
                cursor.execute(sql_verificar, (id_escenario, fecha, hora_fin, hora_inicio, hora_inicio, hora_fin, hora_inicio, hora_fin, hora_inicio))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'El escenario no está disponible en ese horario'}), 400
            
            # Procesar fotografía
            fotografia = request.files.get('fotografia')
            fotografia_path = None
            if fotografia and fotografia.filename and allowed_file(fotografia.filename):
                ext = fotografia.filename.rsplit('.', 1)[1].lower()
                filename = f"sesion_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                fotografia.save(filepath)
                fotografia_path = f"uploads/sesiones/{filename}"
            
            # Procesar logo
            logo = request.files.get('logo')
            logo_path = None
            if tipo_procedencia == 'institucion' and logo and logo.filename and allowed_file(logo.filename):
                ext = logo.filename.rsplit('.', 1)[1].lower()
                filename = f"logo_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                logo.save(filepath)
                logo_path = f"uploads/sesiones/{filename}"
            
            with conexion.cursor() as cursor:
                sql = """
                    INSERT INTO sesion (sede, nombre_de_sesion, fecha, fotografia, nombre_ponente, apellido_paterno, apellido_materno, perfil_profesional, biografia, id_tipo_sesion, hora_inicio, hora_fin, cupo_audiencia, id_carrera, id_escenario, procedencia_institucion_independiente, logo, id_evento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (sede, nombre_de_sesion, fecha, fotografia_path, nombre_ponente, apellido_paterno, apellido_materno, perfil_profesional, biografia, id_tipo_sesion, hora_inicio, hora_fin, cupo_audiencia, id_carrera, id_escenario, nombre_institucion, logo_path, id_evento))
                conexion.commit()
            
            return jsonify({'success': True, 'message': 'Sesión registrada exitosamente', 'redirect': '/admin/sesiones'})
            
        except Exception as e:
            if conexion:
                conexion.rollback()
            print(f"Error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            if conexion:
                conexion.close()
    
    # GET
    conexion = config.conectar_db()
    tipos_sesion = escenarios = carreras = eventos = []
    
    if conexion:
        try:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT * FROM tipo_sesion")
                tipos_sesion = cursor.fetchall()
                cursor.execute("SELECT * FROM escenarios")
                escenarios = cursor.fetchall()
                cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
                carreras = cursor.fetchall()
                cursor.execute("SELECT id_evento, nombre, fecha_inicio, fecha_fin, activo FROM evento ORDER BY activo DESC, fecha_inicio DESC")
                eventos = cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            conexion.close()
    
    return render_template('admin_nueva_sesion.html', tipos_sesion=tipos_sesion, escenarios=escenarios, carreras=carreras, eventos=eventos)

@admin_bp.route('/ver-sesion')
def admin_ver_sesion():
    if not session.get('admin_logged'):
        return redirect(url_for('auth.login'))
    
    sesion_id = request.args.get('id')
    conexion = config.conectar_db()
    
    if not conexion:
        return "<h3>Error de conexión</h3>", 500
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT s.*, ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre,
                       c.nombre_carrera as carrera_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                LEFT JOIN carreras c ON s.id_carrera = c.id_carrera
                WHERE s.id_sesion = %s
            """, (sesion_id,))
            sesion = cursor.fetchone()
            
            if not sesion:
                return "<h3>Sesión no encontrada</h3>", 404
            
            # Convertir horas
            def convertir_hora(valor):
                if valor is None:
                    return 'N/A'
                if hasattr(valor, 'strftime'):
                    return valor.strftime('%H:%M')
                elif hasattr(valor, 'seconds'):
                    horas = valor.seconds // 3600
                    minutos = (valor.seconds % 3600) // 60
                    return f"{horas:02d}:{minutos:02d}"
                return str(valor)[:5]
            
            sesion['hora_inicio_str'] = convertir_hora(sesion.get('hora_inicio'))
            sesion['hora_fin_str'] = convertir_hora(sesion.get('hora_fin'))
            sesion['fecha_str'] = sesion['fecha'].strftime('%d/%m/%Y') if hasattr(sesion.get('fecha'), 'strftime') else 'N/A'
            
            return render_template('admin_ver_sesion.html', sesion=sesion)
    except Exception as e:
        print(f"Error: {e}")
        return f"<h3>Error: {str(e)}</h3>", 500
    finally:
        conexion.close()

@admin_bp.route('/sesion/editar/<int:id>', methods=['GET', 'POST'])
def admin_editar_sesion(id):
    if not session.get('admin_logged'):
        return redirect(url_for('auth.login'))
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('admin.admin_sesiones'))
    
    if request.method == 'POST':
        try:
            id_evento = request.form.get('id_evento')
            sede = request.form.get('sede')
            nombre_de_sesion = request.form.get('nombre_de_sesion')
            fecha = request.form.get('fecha')
            nombre_ponente = request.form.get('nombre_ponente')
            apellido_paterno = request.form.get('apellido_paterno')
            apellido_materno = request.form.get('apellido_materno')
            perfil_profesional = request.form.get('perfil_profesional')
            biografia = request.form.get('biografia')
            id_tipo_sesion = request.form.get('id_tipo_sesion')
            hora_inicio = request.form.get('hora_inicio')
            hora_fin = request.form.get('hora_fin')
            cupo_audiencia = request.form.get('cupo_audiencia')
            id_carrera = request.form.get('id_carrera') or None
            id_escenario = request.form.get('id_escenario')
            descripcion_materiales = request.form.get('descripcion_materiales')
            procedencia = request.form.get('procedencia_institucion_independiente')
            
            if not validar_horas(hora_inicio, hora_fin):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'La hora de fin debe ser posterior a la hora de inicio'})
                flash('La hora de fin debe ser posterior a la hora de inicio', 'error')
                return redirect(url_for('admin.admin_editar_sesion', id=id))
            
            # Procesar fotografía
            fotografia = request.files.get('fotografia')
            fotografia_path = None
            if fotografia and fotografia.filename and allowed_file(fotografia.filename):
                ext = fotografia.filename.rsplit('.', 1)[1].lower()
                filename = f"sesion_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                fotografia.save(filepath)
                fotografia_path = f"uploads/sesiones/{filename}"
            
            # Procesar logo
            logo = request.files.get('logo')
            logo_path = None
            if logo and logo.filename and allowed_file(logo.filename):
                ext = logo.filename.rsplit('.', 1)[1].lower()
                filename = f"logo_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                logo.save(filepath)
                logo_path = f"uploads/sesiones/{filename}"
            
            with conexion.cursor() as cursor:
                sql = """
                    UPDATE sesion SET
                        sede = %s, nombre_de_sesion = %s, fecha = %s,
                        nombre_ponente = %s, apellido_paterno = %s, apellido_materno = %s,
                        perfil_profesional = %s, biografia = %s, id_tipo_sesion = %s,
                        hora_inicio = %s, hora_fin = %s, cupo_audiencia = %s,
                        descripcion_materiales = %s, id_carrera = %s, id_escenario = %s,
                        procedencia_institucion_independiente = %s, id_evento = %s
                """
                params = [sede, nombre_de_sesion, fecha, nombre_ponente, apellido_paterno,
                          apellido_materno, perfil_profesional, biografia, id_tipo_sesion,
                          hora_inicio, hora_fin, cupo_audiencia, descripcion_materiales,
                          id_carrera, id_escenario, procedencia, id_evento]
                
                if fotografia_path:
                    sql += ", fotografia = %s"
                    params.append(fotografia_path)
                if logo_path:
                    sql += ", logo = %s"
                    params.append(logo_path)
                
                sql += " WHERE id_sesion = %s"
                params.append(id)
                
                cursor.execute(sql, params)
                conexion.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Sesión actualizada exitosamente'})
            
            flash('Sesión actualizada exitosamente', 'success')
            return redirect(url_for('admin.admin_sesiones'))
            
        except Exception as e:
            conexion.rollback()
            print(f"Error: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)}), 500
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('admin.admin_editar_sesion', id=id))
        finally:
            conexion.close()
    
    # GET
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM sesion WHERE id_sesion = %s", (id,))
            sesion = cursor.fetchone()
            
            if not sesion:
                flash('Sesión no encontrada', 'error')
                return redirect(url_for('admin.admin_sesiones'))
            
            if sesion.get('fecha'):
                sesion['fecha_str'] = sesion['fecha'].strftime('%Y-%m-%d')
            
            def convertir_hora(valor):
                if valor is None:
                    return None
                if hasattr(valor, 'strftime'):
                    return valor.strftime('%H:%M')
                elif hasattr(valor, 'seconds'):
                    horas = valor.seconds // 3600
                    minutos = (valor.seconds % 3600) // 60
                    return f"{horas:02d}:{minutos:02d}"
                return str(valor)[:5] if valor else None
            
            sesion['hora_inicio_str'] = convertir_hora(sesion.get('hora_inicio'))
            sesion['hora_fin_str'] = convertir_hora(sesion.get('hora_fin'))
            
            cursor.execute("SELECT * FROM tipo_sesion")
            tipos_sesion = cursor.fetchall()
            cursor.execute("SELECT * FROM escenarios")
            escenarios = cursor.fetchall()
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
            cursor.execute("SELECT id_evento, nombre, fecha_inicio, fecha_fin, activo FROM evento ORDER BY activo DESC, fecha_inicio DESC")
            eventos = cursor.fetchall()
            
    except Exception as e:
        print(f"Error: {e}")
        flash('Error al cargar la sesión', 'error')
        return redirect(url_for('admin.admin_sesiones'))
    finally:
        conexion.close()
    
    return render_template('admin_editar_sesion.html', sesion=sesion, tipos_sesion=tipos_sesion, escenarios=escenarios, carreras=carreras, eventos=eventos)

@admin_bp.route('/sesion/eliminar/<int:id>', methods=['POST'])
def admin_eliminar_sesion(id):
    if not session.get('admin_logged'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    conexion = config.conectar_db()
    if not conexion:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT fotografia, logo FROM sesion WHERE id_sesion = %s", (id,))
            archivos = cursor.fetchone()
            cursor.execute("DELETE FROM sesion WHERE id_sesion = %s", (id,))
            conexion.commit()
            
            if archivos:
                if archivos.get('fotografia'):
                    ruta = os.path.join('static', archivos['fotografia'])
                    if os.path.exists(ruta):
                        os.remove(ruta)
                if archivos.get('logo'):
                    ruta = os.path.join('static', archivos['logo'])
                    if os.path.exists(ruta):
                        os.remove(ruta)
            
        return jsonify({'success': True, 'message': 'Sesión eliminada'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conexion.close()

# ==================== GESTIÓN DE USUARIOS ====================
@admin_bp.route('/usuarios', methods=['GET'])
def admin_usuarios_lista():
    if not session.get('admin_logged'):
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('auth.login'))
    
    conexion = config.conectar_db()
    carreras = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conexion.close()
    
    return render_template('admin_usuarios.html', carreras=carreras)

@admin_bp.route('/verificar_disponibilidad', methods=['POST'])
def verificar_disponibilidad():
    try:
        data = request.get_json()
        id_escenario = data.get('id_escenario')
        fecha = data.get('fecha')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        id_sesion_actual = data.get('id_sesion', None)
        
        if not all([id_escenario, fecha, hora_inicio, hora_fin]):
            return jsonify({'disponible': False, 'mensaje': 'Faltan datos'})
        
        conexion = config.conectar_db()
        if not conexion:
            return jsonify({'disponible': False, 'mensaje': 'Error de conexión'})
        
        with conexion.cursor() as cursor:
            sql = """
                SELECT id_sesion, nombre_de_sesion, hora_inicio, hora_fin
                FROM sesion 
                WHERE id_escenario = %s AND fecha = %s
                AND (
                    (hora_inicio < %s AND hora_fin > %s) OR
                    (hora_inicio BETWEEN %s AND %s) OR
                    (hora_fin BETWEEN %s AND %s) OR
                    (%s BETWEEN hora_inicio AND hora_fin)
                )
            """
            if id_sesion_actual:
                sql += " AND id_sesion != %s"
                params = (id_escenario, fecha, hora_fin, hora_inicio, hora_inicio, hora_fin, hora_inicio, hora_fin, hora_inicio, id_sesion_actual)
            else:
                params = (id_escenario, fecha, hora_fin, hora_inicio, hora_inicio, hora_fin, hora_inicio, hora_fin, hora_inicio)
            
            cursor.execute(sql, params)
            conflicto = cursor.fetchone()
            
            if conflicto:
                return jsonify({'disponible': False, 'mensaje': f'El escenario ya está ocupado de {conflicto["hora_inicio"]} a {conflicto["hora_fin"]}'})
            
            return jsonify({'disponible': True, 'mensaje': 'Escenario disponible'})
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'disponible': False, 'mensaje': 'Error al verificar'})
    finally:
        if conexion:
            conexion.close()