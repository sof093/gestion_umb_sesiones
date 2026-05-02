from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
import os
import uuid
import re
from datetime import datetime, date
from werkzeug.utils import secure_filename
import config
from werkzeug.security import generate_password_hash, check_password_hash
# ==================== FUNCIONES DE VALIDACIÓN ====================

def validar_solo_letras(texto):
    """Valida que el texto solo contenga letras y espacios"""
    if not texto:
        return True
    return bool(re.match(r'^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$', texto))

def validar_numero_positivo(valor):
    """Valida que el número sea positivo"""
    if not valor:
        return True
    try:
        num = int(valor)
        return num > 0
    except ValueError:
        return False

def validar_horas(hora_inicio, hora_fin):
    if not hora_inicio or not hora_fin:
        return True
    
    def hora_a_minutos(hora_str):
        hora_str = str(hora_str).strip()
        
        patron = re.match(r'^(\d{1,2}):(\d{2})(?::\d{2})?$', hora_str)
        if patron:
            return int(patron.group(1)) * 60 + int(patron.group(2))
        return 0
    
    minutos_inicio = hora_a_minutos(hora_inicio)
    minutos_fin = hora_a_minutos(hora_fin)
    
    print(f"DEBUG - Inicio: '{hora_inicio}' -> {minutos_inicio} min")
    print(f"DEBUG - Fin: '{hora_fin}' -> {minutos_fin} min")
    
    return minutos_inicio < minutos_fin

def validar_fecha_no_pasada(fecha_str):
    """Valida que la fecha no sea anterior al día actual"""
    if not fecha_str:
        return True
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        return fecha >= date.today()
    except:
        return False

# ==================== CONFIGURACIÓN ====================

app = config.app
app.config['UPLOAD_FOLDER'] = 'static/uploads/sesiones'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== RUTAS PRINCIPALES ====================

@app.route('/')
def index():
    """Página de inicio de sesión"""
    return render_template('index.html')

@app.route('/login_admin', methods=['POST'])
def login_admin():
    """Autenticación del administrador"""
    email = request.form.get('usuario')  # Ahora es email, no número empleado
    password = request.form.get('password')
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión a la base de datos', 'error')
        return redirect(url_for('index'))
    
    try:
        with conexion.cursor() as cursor:
            # CAMBIO IMPORTANTE: Buscar por email y NO comparar password aquí
            sql = "SELECT * FROM administrador WHERE email = %s"
            cursor.execute(sql, (email,))
            admin = cursor.fetchone()
            
            if admin:
                # VERIFICAR CONTRASEÑA CON HASH
                if check_password_hash(admin['password'], password):
                    session['admin_logged'] = True
                    session['admin_id'] = admin['id_control']
                    session['admin_nombre'] = admin['nombre_admin']
                    session['admin_email'] = admin['email']  # Guardar email
                    flash(f'Bienvenido {admin["nombre_admin"]}', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Contraseña incorrecta', 'error')
            else:
                flash('Credenciales incorrectas', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        print(f"Error en login: {e}")
        flash('Error al iniciar sesión', 'error')
        return redirect(url_for('index'))
    finally:
        conexion.close()

@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('index'))

# ==================== DASHBOARD ADMIN ====================

@app.route('/admin/dashboard')
def admin_dashboard():
    """Panel principal del administrador"""
    if not session.get('admin_logged'):
        flash('Debe iniciar sesión primero', 'warning')
        return redirect(url_for('index'))
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('index'))
    
    try:
        with conexion.cursor() as cursor:
            # Total de sesiones
            cursor.execute("SELECT COUNT(*) as total FROM sesion")
            total_sesiones = cursor.fetchone()['total']
            
            # Sesiones por tipo
            cursor.execute("""
                SELECT ts.nombre_sesion, COUNT(s.id_sesion) as total 
                FROM tipo_sesion ts
                LEFT JOIN sesion s ON ts.id_tipo_sesion = s.id_tipo_sesion
                GROUP BY ts.id_tipo_sesion
            """)
            sesiones_por_tipo = cursor.fetchall()
            
            # Próximas sesiones (futuras)
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

@app.route('/admin/sesiones')
def admin_sesiones():
    """Listado de todas las sesiones"""
    if not session.get('admin_logged'):
        return redirect(url_for('index'))
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('admin_dashboard'))
    
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

@app.route('/admin/sesion/nueva', methods=['GET', 'POST'])
def nueva_sesion():
    """Registrar una nueva sesión"""
    if not session.get('admin_logged'):
        return redirect(url_for('index'))
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
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
            
            # ============================================
            # VALIDACIONES DE BACKEND
            # ============================================
            
            # Validar nombres (solo letras)
            if not validar_solo_letras(nombre_ponente):
                flash('El nombre del ponente solo puede contener letras', 'error')
                return redirect(url_for('nueva_sesion'))

            if not validar_solo_letras(apellido_paterno):
                flash('El apellido paterno solo puede contener letras', 'error')
                return redirect(url_for('nueva_sesion'))

            if apellido_materno and not validar_solo_letras(apellido_materno):
                flash('El apellido materno solo puede contener letras', 'error')
                return redirect(url_for('nueva_sesion'))

            # Validar cupo
            if cupo_audiencia and not validar_numero_positivo(cupo_audiencia):
                flash('El cupo debe ser un número mayor a 0', 'error')
                return redirect(url_for('nueva_sesion'))

            # Validar horas
            if not validar_horas(hora_inicio, hora_fin):
                flash('La hora de fin debe ser posterior a la hora de inicio', 'error')
                return redirect(url_for('nueva_sesion'))

            # Validar fecha (no pasada)
            if not validar_fecha_no_pasada(fecha):
                flash('La fecha no puede ser anterior al día de hoy', 'error')
                return redirect(url_for('nueva_sesion'))
            
            # ============================================
            # FIN DE VALIDACIONES
            # ============================================
            
            # --- 2. Lógica para el campo 'procedencia_institucion_independiente' ---
            tipo_procedencia = request.form.get('tipo_procedencia')
            nombre_institucion = None
            if tipo_procedencia == 'institucion':
                nombre_institucion = request.form.get('procedencia_institucion_independiente')
                if not nombre_institucion:
                    flash('Por favor, ingrese el nombre de la institución', 'error')
                    return redirect(url_for('nueva_sesion'))
            
            # --- 3. Lógica para el campo 'descripcion_materiales' ---
            requiere_materiales = request.form.get('requiere_materiales')
            descripcion_materiales = None
            if requiere_materiales == 'si':
                descripcion_materiales = request.form.get('descripcion_materiales')
                if not descripcion_materiales:
                    flash('Por favor, describa los materiales necesarios', 'error')
                    return redirect(url_for('nueva_sesion'))
            
            # --- 4. Procesar fotografía del ponente ---
            fotografia = request.files.get('fotografia')
            fotografia_path = None
            if fotografia and fotografia.filename and allowed_file(fotografia.filename):
                ext = fotografia.filename.rsplit('.', 1)[1].lower()
                filename = f"sesion_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                fotografia.save(filepath)
                fotografia_path = f"uploads/sesiones/{filename}"
            elif fotografia and fotografia.filename:
                # Si se subió un archivo pero no es válido
                flash('El archivo de fotografía debe ser una imagen (JPG, PNG, GIF, WEBP)', 'error')
                return redirect(url_for('nueva_sesion'))
            
            # --- 5. Procesar logo institucional ---
            logo = request.files.get('logo')
            logo_path = None
            if tipo_procedencia == 'institucion' and logo and logo.filename:
                if allowed_file(logo.filename):
                    ext = logo.filename.rsplit('.', 1)[1].lower()
                    filename = f"logo_{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logo.save(filepath)
                    logo_path = f"uploads/sesiones/{filename}"
                else:
                    flash('El archivo de logo debe ser una imagen (JPG, PNG, GIF, WEBP)', 'error')
                    return redirect(url_for('nueva_sesion'))
            
            # --- 6. Insertar en la base de datos ---
            with conexion.cursor() as cursor:
                sql = """
                    INSERT INTO sesion (
                        sede,nombre_de_sesion, fecha, fotografia, nombre_ponente, apellido_paterno, 
                        apellido_materno, perfil_profesional, biografia, id_tipo_sesion,
                        hora_inicio, hora_fin, cupo_audiencia, descripcion_materiales,
                        id_carrera, id_escenario, procedencia_institucion_independiente, logo
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(sql, (
                    sede, nombre_de_sesion,fecha, fotografia_path, nombre_ponente, apellido_paterno,
                    apellido_materno, perfil_profesional, biografia, id_tipo_sesion,
                    hora_inicio, hora_fin, cupo_audiencia, descripcion_materiales,
                    id_carrera, id_escenario, nombre_institucion, logo_path
                ))
                conexion.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Sesión registrada exitosamente',
                'redirect': '/admin/sesiones'
            })
            
        except Exception as e:
            conexion.rollback()
            print(f"Error al registrar sesión: {e}")
            return jsonify({
                'success': False, 
                'message': f'Error: {str(e)}'
            }), 500
        finally:
            conexion.close()
    
    # --- Método GET: Cargar datos para selects ---
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM tipo_sesion")
            tipos_sesion = cursor.fetchall()
            
            cursor.execute("SELECT * FROM escenarios")
            escenarios = cursor.fetchall()
            
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
    finally:
        conexion.close()
    
    return render_template('admin_nueva_sesion.html', 
                         tipos_sesion=tipos_sesion,
                         escenarios=escenarios,
                         carreras=carreras)

@app.route('/api/tipos-sesion')
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

@app.route('/api/escenarios')
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

@app.route('/api/carreras')
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

@app.route('/admin/sesion/editar/<int:id>', methods=['GET', 'POST'])
def admin_editar_sesion(id):
    """Editar una sesión existente"""
    if not session.get('admin_logged'):
        return redirect(url_for('index'))
    
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('admin_sesiones'))
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre_ponente = request.form.get('nombre_ponente')
            apellido_paterno = request.form.get('apellido_paterno')
            apellido_materno = request.form.get('apellido_materno')
            cupo_audiencia = request.form.get('cupo_audiencia')
            hora_inicio = request.form.get('hora_inicio')
            hora_fin = request.form.get('hora_fin')
            fecha = request.form.get('fecha')
            
            # Validaciones de backend también en edición
            if not validar_solo_letras(nombre_ponente):
                flash('El nombre del ponente solo puede contener letras', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            if not validar_solo_letras(apellido_paterno):
                flash('El apellido paterno solo puede contener letras', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            if apellido_materno and not validar_solo_letras(apellido_materno):
                flash('El apellido materno solo puede contener letras', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            if cupo_audiencia and not validar_numero_positivo(cupo_audiencia):
                flash('El cupo debe ser un número mayor a 0', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            if not validar_horas(hora_inicio, hora_fin):
                flash('La hora de fin debe ser posterior a la hora de inicio', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            if not validar_fecha_no_pasada(fecha):
                flash('La fecha no puede ser anterior al día de hoy', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            # Actualizar sesión
            with conexion.cursor() as cursor:
                sql = """
                    UPDATE sesion SET
                        sede = %s, fecha = %s, nombre_ponente = %s,
                        apellido_paterno = %s, apellido_materno = %s,
                        perfil_profesional = %s, biografia = %s,
                        id_tipo_sesion = %s, hora_inicio = %s, hora_fin = %s,
                        cupo_audiencia = %s, descripcion_materiales = %s,
                        id_carrera = %s, id_escenario = %s,
                        procedencia_institucion_independiente = %s
                    WHERE id_sesion = %s
                """
                cursor.execute(sql, (
                    request.form.get('sede'), request.form.get('fecha'),
                    request.form.get('nombre_ponente'), request.form.get('apellido_paterno'),
                    request.form.get('apellido_materno'), request.form.get('perfil_profesional'),
                    request.form.get('biografia'), request.form.get('id_tipo_sesion'),
                    request.form.get('hora_inicio'), request.form.get('hora_fin'),
                    request.form.get('cupo_audiencia'), request.form.get('descripcion_materiales'),
                    request.form.get('id_carrera') or None, request.form.get('id_escenario'),
                    request.form.get('procedencia_institucion_independiente'), id
                ))
                conexion.commit()
                
            flash('Sesión actualizada exitosamente', 'success')
            return redirect(url_for('admin_sesiones'))
            
        except Exception as e:
            conexion.rollback()
            flash(f'Error al actualizar: {str(e)}', 'error')
        finally:
            conexion.close()
    
    # GET - Cargar datos de la sesión
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM sesion WHERE id_sesion = %s", (id,))
            sesion = cursor.fetchone()
            
            if not sesion:
                flash('Sesión no encontrada', 'error')
                return redirect(url_for('admin_sesiones'))
            
            cursor.execute("SELECT * FROM tipo_sesion")
            tipos_sesion = cursor.fetchall()
            
            cursor.execute("SELECT * FROM escenarios")
            escenarios = cursor.fetchall()
            
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
    finally:
        conexion.close()
    
    return render_template('admin_editar_sesion.html', 
                         sesion=sesion,
                         tipos_sesion=tipos_sesion,
                         escenarios=escenarios,
                         carreras=carreras)

@app.route('/admin/sesion/eliminar/<int:id>', methods=['POST'])
def admin_eliminar_sesion(id):
    """Eliminar una sesión"""
    if not session.get('admin_logged'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    conexion = config.conectar_db()
    if not conexion:
        return jsonify({'success': False, 'message': 'Error de conexión'}), 500
    
    try:
        with conexion.cursor() as cursor:
            # Obtener rutas de archivos para eliminarlos
            cursor.execute("SELECT fotografia, logo FROM sesion WHERE id_sesion = %s", (id,))
            archivos = cursor.fetchone()
            
            # Eliminar de la BD
            cursor.execute("DELETE FROM sesion WHERE id_sesion = %s", (id,))
            conexion.commit()
            
            # Eliminar archivos físicos
            if archivos:
                if archivos.get('fotografia'):
                    ruta_foto = os.path.join('static', archivos['fotografia'])
                    if os.path.exists(ruta_foto):
                        os.remove(ruta_foto)
                if archivos.get('logo'):
                    ruta_logo = os.path.join('static', archivos['logo'])
                    if os.path.exists(ruta_logo):
                        os.remove(ruta_logo)
            
        return jsonify({'success': True, 'message': 'Sesión eliminada'})
    except Exception as e:
        print(f"Error al eliminar: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conexion.close()

# ==================== API PARA OBTENER DATOS (AJAX) ====================

@app.route('/api/sesiones')
def api_sesiones():
    """API para obtener todas las sesiones"""
    if not session.get('admin_logged'):
        return jsonify([])
    
    conexion = config.conectar_db()
    if not conexion:
        return jsonify([])
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    s.id_sesion,
                    s.sede,
                    s.nombre_de_sesion,
                    s.fecha,
                    s.fotografia,
                    s.nombre_ponente,
                    s.apellido_paterno,
                    s.apellido_materno,
                    s.perfil_profesional,
                    s.biografia,
                    s.id_tipo_sesion,
                    s.hora_inicio,
                    s.hora_fin,
                    s.cupo_audiencia,
                    s.descripcion_materiales,
                    s.id_carrera,
                    s.id_escenario,
                    s.procedencia_institucion_independiente,
                    s.logo,
                    ts.nombre_sesion as tipo,
                    e.nombre_escenario as escenario_nombre,
                    c.nombre_carrera as carrera_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                LEFT JOIN carreras c ON s.id_carrera = c.id_carrera
                ORDER BY s.fecha DESC, s.hora_inicio ASC
            """)
            sesiones = cursor.fetchall()
            
            print(f"DEBUG: Se encontraron {len(sesiones)} sesiones")
            
            # Convertir a lista de diccionarios compatible con JSON
            resultado = []
            for sesion in sesiones:
                item = dict(sesion)
                
                # Convertir fecha a string
                if item.get('fecha'):
                    item['fecha_str'] = item['fecha'].strftime('%d/%m/%Y')
                    item['fecha'] = item['fecha'].strftime('%Y-%m-%d')
                
                # Convertir hora_inicio (timedelta a string HH:MM)
                if item.get('hora_inicio'):
                    if hasattr(item['hora_inicio'], 'seconds'):
                        # Es timedelta
                        total_seconds = item['hora_inicio'].seconds
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        item['hora_inicio_str'] = f"{hours:02d}:{minutes:02d}"
                        item['hora_inicio'] = f"{hours:02d}:{minutes:02d}"
                    elif hasattr(item['hora_inicio'], 'strftime'):
                        # Es time
                        item['hora_inicio_str'] = item['hora_inicio'].strftime('%H:%M')
                        item['hora_inicio'] = item['hora_inicio'].strftime('%H:%M')
                    else:
                        # Es string
                        item['hora_inicio_str'] = str(item['hora_inicio'])[:5]
                        item['hora_inicio'] = str(item['hora_inicio'])[:5]
                else:
                    item['hora_inicio_str'] = None
                
                # Convertir hora_fin (timedelta a string HH:MM)
                if item.get('hora_fin'):
                    if hasattr(item['hora_fin'], 'seconds'):
                        # Es timedelta
                        total_seconds = item['hora_fin'].seconds
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        item['hora_fin_str'] = f"{hours:02d}:{minutes:02d}"
                        item['hora_fin'] = f"{hours:02d}:{minutes:02d}"
                    elif hasattr(item['hora_fin'], 'strftime'):
                        # Es time
                        item['hora_fin_str'] = item['hora_fin'].strftime('%H:%M')
                        item['hora_fin'] = item['hora_fin'].strftime('%H:%M')
                    else:
                        # Es string
                        item['hora_fin_str'] = str(item['hora_fin'])[:5]
                        item['hora_fin'] = str(item['hora_fin'])[:5]
                else:
                    item['hora_fin_str'] = None
                
                # Asegurar que otros campos sean serializables
                if item.get('cupo_audiencia') is None:
                    item['cupo_audiencia'] = 0
                
                resultado.append(item)
            
            print(f"DEBUG: Enviando {len(resultado)} sesiones al frontend")
            return jsonify(resultado)
            
    except Exception as e:
        print(f"DEBUG Error en API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])
    finally:
        conexion.close()

@app.route('/api/test-sesiones')
def test_sesiones():
    """Endpoint de prueba para verificar la conexión"""
    if not session.get('admin_logged'):
        return jsonify({'error': 'No autorizado'}), 401
    
    conexion = config.conectar_db()
    if not conexion:
        return jsonify({'error': 'Error de conexión'}), 500
    
    try:
        with conexion.cursor() as cursor:
            # Consulta simple
            cursor.execute("SELECT COUNT(*) as total FROM sesion")
            count = cursor.fetchone()
            
            cursor.execute("SELECT id_sesion, nombre_ponente, apellido_paterno FROM sesion LIMIT 5")
            sesiones = cursor.fetchall()
            
            return jsonify({
                'total': count['total'],
                'sesiones': list(sesiones)
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conexion.close()
        

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)