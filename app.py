#app.py`
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
import os
import uuid
import re
from datetime import datetime, date
from werkzeug.utils import secure_filename
import config
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import secrets
from datetime import datetime, timedelta
import secrets
from datetime import datetime, timedelta

# ==================== CONFIGURACIÓN DE CORREO ====================
app = config.app

app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Para Gmail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'administradorsesionesumb@gmail.com'  # CAMBIA ESTO
app.config['MAIL_PASSWORD'] = 'qaun eayw roid ebrp'  # CAMBIA ESTO
app.config['MAIL_DEFAULT_SENDER'] = 'administradorsesionesumb@gmail.com'

mail = Mail(app)

# ==================== FUNCIONES DE CORREO ====================

def enviar_correo(destinatario, asunto, cuerpo_html, cuerpo_texto=None):
    """Función genérica para enviar correos"""
    try:
        msg = Message(asunto, recipients=[destinatario])
        msg.html = cuerpo_html
        if cuerpo_texto:
            msg.body = cuerpo_texto
        mail.send(msg)
        print(f"✅ Correo enviado a {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo a {destinatario}: {e}")
        return False


def enviar_credenciales_usuario(nombre, email, password_temporal, rol):
    """Envía correo con credenciales temporales al usuario nuevo"""
    asunto = f"Bienvenido al Sistema de Gestión UES - Credenciales de acceso"
    
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1a3a2a; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background: #f5f5f5; }}
            .credentials {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; }}
            .footer {{ text-align: center; padding: 15px; font-size: 12px; color: #777; }}
            .badge {{ display: inline-block; padding: 5px 10px; border-radius: 20px; font-size: 12px; }}
            .admin {{ background: #c8a84b; color: #1a3a2a; }}
            .alumno {{ background: #2d5a3d; color: white; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🎓 UES San José del Rincón</h2>
                <p>Sistema de Gestión de Jornadas Académicas</p>
            </div>
            <div class="content">
                <h3>¡Hola, {nombre}!</h3>
                <p>Se ha creado tu cuenta en el sistema como 
                   <span class="badge {'admin' if rol == 'admin' else 'alumno'}">
                       {'Administrador' if rol == 'admin' else 'Alumno'}
                   </span>
                </p>
                <p>Estas son tus credenciales de acceso temporal:</p>
                <div class="credentials">
                    <p><strong>📧 Correo:</strong> {email}</p>
                    <p><strong>🔑 Contraseña temporal:</strong> <code>{password_temporal}</code></p>
                </div>
                <p><strong>⚠️ Importante:</strong> Al iniciar sesión por primera vez, deberás cambiar tu contraseña.</p>
                <p><a href="http://localhost:5000/login" style="background: #1a3a2a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Iniciar sesión</a></p>
            </div>
            <div class="footer">
                <p>© 2026 UES San José del Rincón - Todos los derechos reservados.</p>
                <p>Este es un mensaje automático, por favor no responder.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return enviar_correo(email, asunto, cuerpo_html)


def enviar_enlace_recuperacion(email, nombre, token, tipo_usuario):
    """Envía correo con enlace para recuperar contraseña"""
    enlace = f"http://localhost:5000/recuperar-password?token={token}&tipo={tipo_usuario}"
    
    asunto = "Recuperación de contraseña - UES San José del Rincón"
    
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1a3a2a; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background: #f5f5f5; }}
            .link-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; word-break: break-all; }}
            .footer {{ text-align: center; padding: 15px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🔐 Recuperación de contraseña</h2>
            </div>
            <div class="content">
                <h3>Hola, {nombre}</h3>
                <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
                <div class="link-box">
                    <a href="{enlace}" style="color: #1a3a2a; font-weight: bold;">Restablecer mi contraseña</a>
                </div>
                <p>O copia este enlace en tu navegador:</p>
                <p style="font-size: 12px; color: #777; word-break: break-all;">{enlace}</p>
                <p><strong>⚠️ Este enlace expirará en 24 horas.</strong></p>
                <p>Si no solicitaste este cambio, ignora este mensaje.</p>
            </div>
            <div class="footer">
                <p>© 2026 UES San José del Rincón</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return enviar_correo(email, asunto, cuerpo_html)

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login que detecta automáticamente si es admin o alumno"""
    if request.method == 'GET':
        return render_template('index.html')
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not email or not password:
        flash('Todos los campos son requeridos', 'error')
        return redirect(url_for('login'))
    
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            # ============================================
            # 1. BUSCAR EN TABLA ADMINISTRADOR
            # ============================================
            cursor.execute("SELECT * FROM administrador WHERE email = %s", (email,))
            admin = cursor.fetchone()
            
            if admin and check_password_hash(admin['password'], password):
                # Es ADMINISTRADOR
                session.clear()
                session['user_id'] = admin['id_control']
                session['user_nombre'] = admin['nombre_admin']
                session['user_email'] = admin['email']
                session['user_tipo'] = 'admin'
                session['admin_logged'] = True
                
                # ✅ Verificar primer login
                if admin.get('primer_login', True):
                    flash('Es tu primer inicio de sesión. Debes cambiar tu contraseña.', 'warning')
                    return redirect(url_for('cambiar_password'))
                
                flash(f'Bienvenido Administrador {admin["nombre_admin"]}', 'success')
                return redirect(url_for('admin_dashboard'))
            
            # ============================================
            # 2. BUSCAR EN TABLA ALUMNOS
            # ============================================
            cursor.execute("SELECT * FROM alumnos WHERE correo_electronico = %s", (email,))
            alumno = cursor.fetchone()
            
            if alumno and check_password_hash(alumno['password'], password):
                # Es ALUMNO
                session.clear()
                session['user_id'] = alumno['id_alumno']
                session['user_nombre'] = f"{alumno['nombre_alumno']} {alumno['apellido_paterno']}"
                session['user_email'] = alumno['correo_electronico']
                session['user_tipo'] = 'alumno'
                
                # ✅ Verificar primer login
                if alumno.get('primer_login', True):
                    flash('Es tu primer inicio de sesión. Debes cambiar tu contraseña.', 'warning')
                    return redirect(url_for('cambiar_password'))
                
                flash(f'Bienvenido {alumno["nombre_alumno"]}', 'success')
                return redirect(url_for('alumno_dashboard'))
            
            # ============================================
            # 3. NO EXISTE EN NINGUNA TABLA
            # ============================================
            flash('Credenciales incorrectas. Verifica tu correo y contraseña.', 'error')
            
    except Exception as e:
        print(f"Error en login: {e}")
        flash('Error al iniciar sesión', 'error')
    finally:
        conexion.close()
    
    return redirect(url_for('login'))


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
    
    if request.method == 'POST':
        conexion = None
        try:
            # Obtener datos del formulario
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
            
            # DEBUG: Imprimir datos recibidos
            print(f"DEBUG - Datos recibidos: id_evento={id_evento}, fecha={fecha}, tipo={id_tipo_sesion}")
            
            # ============================================
            # VALIDACIONES BÁSICAS
            # ============================================
            if not all([sede, nombre_de_sesion, fecha, nombre_ponente, 
                       apellido_paterno, id_tipo_sesion, hora_inicio, 
                       hora_fin, id_escenario, id_evento]):
                return jsonify({
                    'success': False, 
                    'message': 'Todos los campos obligatorios deben ser llenados'
                }), 400
            
            # Validar evento existe
            if not id_evento or id_evento == '':
                return jsonify({
                    'success': False, 
                    'message': 'Debes seleccionar un evento válido'
                }), 400
            
            conexion = config.conectar_db()
            if not conexion:
                return jsonify({
                    'success': False, 
                    'message': 'Error de conexión a la base de datos'
                }), 500
            
            # Verificar que el evento existe
            with conexion.cursor() as cursor:
                cursor.execute("SELECT id_evento FROM evento WHERE id_evento = %s", (id_evento,))
                if not cursor.fetchone():
                    return jsonify({
                        'success': False, 
                        'message': f'El evento con ID {id_evento} no existe'
                    }), 400
            
            # Validar horas
            if not validar_horas(hora_inicio, hora_fin):
                return jsonify({
                    'success': False, 
                    'message': 'La hora de fin debe ser posterior a la hora de inicio'
                }), 400
            
            # ============================================
            # PROCESAR CAMPOS ADICIONALES
            # ============================================
            
            # Procedencia
            tipo_procedencia = request.form.get('tipo_procedencia')
            nombre_institucion = None
            if tipo_procedencia == 'institucion':
                nombre_institucion = request.form.get('procedencia_institucion_independiente')
            
            # Materiales
            requiere_materiales = request.form.get('requiere_materiales')
            descripcion_materiales = None
            if requiere_materiales == 'si':
                descripcion_materiales = request.form.get('descripcion_materiales')
            
            # Procesar fotografía
            fotografia = request.files.get('fotografia')
            fotografia_path = None
            if fotografia and fotografia.filename:
                if allowed_file(fotografia.filename):
                    ext = fotografia.filename.rsplit('.', 1)[1].lower()
                    filename = f"sesion_{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    fotografia.save(filepath)
                    fotografia_path = f"uploads/sesiones/{filename}"
            
            # Procesar logo
            logo = request.files.get('logo')
            logo_path = None
            if tipo_procedencia == 'institucion' and logo and logo.filename:
                if allowed_file(logo.filename):
                    ext = logo.filename.rsplit('.', 1)[1].lower()
                    filename = f"logo_{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    logo.save(filepath)
                    logo_path = f"uploads/sesiones/{filename}"
            
            # ============================================
            # INSERTAR EN BASE DE DATOS
            # ============================================
            with conexion.cursor() as cursor:
                sql = """
                    INSERT INTO sesion (
                        sede, nombre_de_sesion, fecha, fotografia, 
                        nombre_ponente, apellido_paterno, apellido_materno, 
                        perfil_profesional, biografia, id_tipo_sesion,
                        hora_inicio, hora_fin, cupo_audiencia, descripcion_materiales,
                        id_carrera, id_escenario, procedencia_institucion_independiente, 
                        logo, id_evento
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cursor.execute(sql, (
                    sede, nombre_de_sesion, fecha, fotografia_path,
                    nombre_ponente, apellido_paterno, apellido_materno,
                    perfil_profesional, biografia, id_tipo_sesion,
                    hora_inicio, hora_fin, cupo_audiencia, descripcion_materiales,
                    id_carrera, id_escenario, nombre_institucion,
                    logo_path, id_evento
                ))
                conexion.commit()
                
                nuevo_id = cursor.lastrowid
                print(f"DEBUG - Sesión creada con ID: {nuevo_id} para evento: {id_evento}")
            
            return jsonify({
                'success': True, 
                'message': 'Sesión registrada exitosamente',
                'redirect': '/admin/sesiones'
            })
            
        except pymysql.Error as e:
            if conexion:
                conexion.rollback()
            print(f"Error MySQL: {e}")
            return jsonify({
                'success': False, 
                'message': f'Error de base de datos: {str(e)}'
            }), 500
        except Exception as e:
            if conexion:
                conexion.rollback()
            print(f"Error general: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False, 
                'message': f'Error: {str(e)}'
            }), 500
        finally:
            if conexion:
                conexion.close()
    
    # ============================================
    # MÉTODO GET - Cargar formulario
    # ============================================
    conexion = config.conectar_db()
    if not conexion:
        flash('Error de conexión', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM tipo_sesion")
            tipos_sesion = cursor.fetchall()
            
            cursor.execute("SELECT * FROM escenarios")
            escenarios = cursor.fetchall()
            
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
            
            # Cargar eventos disponibles
            cursor.execute("""
                SELECT id_evento, nombre, fecha_inicio, fecha_fin, activo 
                FROM evento 
                ORDER BY activo DESC, fecha_inicio DESC
            """)
            eventos = cursor.fetchall()
            
    except Exception as e:
        print(f"Error al cargar datos: {e}")
        tipos_sesion = []
        escenarios = []
        carreras = []
        eventos = []
    finally:
        conexion.close()
    
    return render_template('admin_nueva_sesion.html', 
                         tipos_sesion=tipos_sesion,
                         escenarios=escenarios,
                         carreras=carreras,
                         eventos=eventos)

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

@app.route('/admin/ver-sesion')
def admin_ver_sesion():
    """Página para ver detalles de la sesión (se carga en modal)"""
    if not session.get('admin_logged'):
        return redirect(url_for('index'))
    
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
            
            # Convertir timedelta a string de hora
            def convertir_hora(valor):
                if valor is None:
                    return 'N/A'
                if hasattr(valor, 'strftime'):  # Es datetime.time
                    return valor.strftime('%H:%M')
                elif hasattr(valor, 'seconds'):  # Es timedelta
                    horas = valor.seconds // 3600
                    minutos = (valor.seconds % 3600) // 60
                    return f"{horas:02d}:{minutos:02d}"
                return str(valor)[:5]
            
            # Convertir los campos de hora
            sesion['hora_inicio_str'] = convertir_hora(sesion.get('hora_inicio'))
            sesion['hora_fin_str'] = convertir_hora(sesion.get('hora_fin'))
            
            # Convertir fecha a string
            if sesion.get('fecha'):
                sesion['fecha_str'] = sesion['fecha'].strftime('%d/%m/%Y') if hasattr(sesion['fecha'], 'strftime') else str(sesion['fecha'])
            else:
                sesion['fecha_str'] = 'N/A'
            
            return render_template('admin_ver_sesion.html', sesion=sesion)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h3>Error: {str(e)}</h3>", 500
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
            
            # ============================================
            # VALIDACIONES DE BACKEND
            # ============================================
            
            # Validar nombres (solo letras)
            if not validar_solo_letras(nombre_ponente):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'El nombre del ponente solo puede contener letras'})
                flash('El nombre del ponente solo puede contener letras', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))

            if not validar_solo_letras(apellido_paterno):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'El apellido paterno solo puede contener letras'})
                flash('El apellido paterno solo puede contener letras', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))

            if apellido_materno and not validar_solo_letras(apellido_materno):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'El apellido materno solo puede contener letras'})
                flash('El apellido materno solo puede contener letras', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))

            # Validar cupo
            if cupo_audiencia and not validar_numero_positivo(cupo_audiencia):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'El cupo debe ser un número mayor a 0'})
                flash('El cupo debe ser un número mayor a 0', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))

            # Validar horas
            if not validar_horas(hora_inicio, hora_fin):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'La hora de fin debe ser posterior a la hora de inicio'})
                flash('La hora de fin debe ser posterior a la hora de inicio', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))

            # Validar fecha (no pasada)
            if not validar_fecha_no_pasada(fecha):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'La fecha no puede ser anterior al día de hoy'})
                flash('La fecha no puede ser anterior al día de hoy', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            # ============================================
            # FIN DE VALIDACIONES
            # ============================================
            
            # Procesar fotografía si se subió nueva
            fotografia = request.files.get('fotografia')
            fotografia_path = None
            if fotografia and fotografia.filename and allowed_file(fotografia.filename):
                ext = fotografia.filename.rsplit('.', 1)[1].lower()
                filename = f"sesion_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                fotografia.save(filepath)
                fotografia_path = f"uploads/sesiones/{filename}"
            elif fotografia and fotografia.filename:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'El archivo de fotografía debe ser una imagen (JPG, PNG, GIF, WEBP)'})
                flash('El archivo de fotografía debe ser una imagen (JPG, PNG, GIF, WEBP)', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            # Procesar logo si se subió nuevo
            logo = request.files.get('logo')
            logo_path = None
            if logo and logo.filename and allowed_file(logo.filename):
                ext = logo.filename.rsplit('.', 1)[1].lower()
                filename = f"logo_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logo.save(filepath)
                logo_path = f"uploads/sesiones/{filename}"
            elif logo and logo.filename:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'El archivo de logo debe ser una imagen (JPG, PNG, GIF, WEBP)'})
                flash('El archivo de logo debe ser una imagen (JPG, PNG, GIF, WEBP)', 'error')
                return redirect(url_for('admin_editar_sesion', id=id))
            
            # Construir UPDATE dinámico
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
                
                # Agregar campos opcionales si hay archivos nuevos
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
            
            # Verificar si es petición AJAX (desde el JS)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True, 
                    'message': 'Sesión actualizada exitosamente'
                })
            
            flash('Sesión actualizada exitosamente', 'success')
            return redirect(url_for('admin_sesiones'))
            
        except Exception as e:
            conexion.rollback()
            print(f"Error al actualizar: {e}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False, 
                    'message': f'Error al actualizar: {str(e)}'
                }), 500
            
            flash(f'Error al actualizar: {str(e)}', 'error')
            return redirect(url_for('admin_editar_sesion', id=id))
        finally:
            conexion.close()
    
    # ============================================
    # MÉTODO GET - Cargar datos de la sesión
    # ============================================
# ============================================
# MÉTODO GET - Cargar datos de la sesión
# ============================================
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM sesion WHERE id_sesion = %s", (id,))
            sesion = cursor.fetchone()
            
            if not sesion:
                flash('Sesión no encontrada', 'error')
                return redirect(url_for('admin_sesiones'))
            
            # Convertir fecha para el input date
            if sesion.get('fecha'):
                sesion['fecha_str'] = sesion['fecha'].strftime('%Y-%m-%d')
            
            # Convertir horas
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
            
            # Cargar datos para los selects
            cursor.execute("SELECT * FROM tipo_sesion")
            tipos_sesion = cursor.fetchall()
            
            cursor.execute("SELECT * FROM escenarios")
            escenarios = cursor.fetchall()
            
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
            
            # ============================================
            # CARGAR EVENTOS (IGUAL QUE EN NUEVA)
            # ============================================
            cursor.execute("""
                SELECT id_evento, nombre, fecha_inicio, fecha_fin, activo 
                FROM evento 
                ORDER BY activo DESC, fecha_inicio DESC
            """)
            eventos = cursor.fetchall()
            
    except Exception as e:
        print(f"Error al cargar sesión: {e}")
        flash('Error al cargar la sesión', 'error')
        return redirect(url_for('admin_sesiones'))
    finally:
        conexion.close()

    return render_template('admin_editar_sesion.html', 
                        sesion=sesion,
                        tipos_sesion=tipos_sesion,
                        escenarios=escenarios,
                        carreras=carreras,
                        eventos=eventos)  # ← Pasar eventos al template

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

# ==================== API PARA USUARIOS ====================

@app.route('/api/usuarios', methods=['POST'])
def api_crear_usuario():
    """API para crear nuevo usuario CON ENVÍO DE CORREO"""
    if not session.get('admin_logged') and not session.get('user_tipo') == 'admin':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    data = request.get_json()
    rol = data.get('rol')
    nombre = data.get('nombre')
    apellido_paterno = data.get('apellido_paterno')
    apellido_materno = data.get('apellido_materno', '')
    correo = data.get('correo')
    
    if not nombre or not apellido_paterno or not correo:
        return jsonify({'success': False, 'message': 'Faltan campos requeridos'})
    
    nombre_completo = f"{nombre} {apellido_paterno} {apellido_materno}".strip()
    conexion = config.conectar_db()
    
    try:
        if rol == 'alumno':
            matricula = data.get('matricula')
            id_carrera = data.get('id_carrera')
            
            if not matricula:
                return jsonify({'success': False, 'message': 'La matrícula es requerida'})
            
            password_temporal = matricula
            hashed_password = generate_password_hash(password_temporal)
            
            with conexion.cursor() as cursor:
                sql = """
                    INSERT INTO alumnos 
                    (nombre_alumno, apellido_paterno, apellido_materno, 
                     correo_electronico, matricula, password, id_carrera, primer_login)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                """
                cursor.execute(sql, (nombre, apellido_paterno, apellido_materno, 
                                    correo, matricula, hashed_password, id_carrera))
                conexion.commit()
            
            # ✉️ ENVIAR CORREO AL ALUMNO
            enviar_credenciales_usuario(nombre_completo, correo, password_temporal, 'alumno')
            
            return jsonify({
                'success': True, 
                'message': f'Alumno creado. Se ha enviado la contraseña temporal al correo.'
            })
        
        elif rol == 'admin':
            password_temporal = 'Admin123'
            hashed_password = generate_password_hash(password_temporal)
            
            with conexion.cursor() as cursor:
                sql = """
                    INSERT INTO administrador 
                    (nombre_admin, apellido_paterno, apellido_materno, email, password, primer_login)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                """
                cursor.execute(sql, (nombre, apellido_paterno, apellido_materno, 
                                    correo, hashed_password))
                conexion.commit()
            
            # ✉️ ENVIAR CORREO AL ADMINISTRADOR
            enviar_credenciales_usuario(nombre_completo, correo, password_temporal, 'admin')
            
            return jsonify({
                'success': True, 
                'message': f'Administrador creado. Se ha enviado la contraseña temporal al correo.'
            })
        
        else:
            return jsonify({'success': False, 'message': 'Rol no válido'})
            
    except Exception as e:
        conexion.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conexion.close()
@app.route('/api/usuarios', methods=['GET'])
def api_usuarios():
    """API para obtener todos los usuarios (alumnos + administradores)"""
    if not session.get('admin_logged') and not session.get('user_tipo') == 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    
    conexion = config.conectar_db()
    usuarios = []
    
    try:
        with conexion.cursor() as cursor:
            # Obtener alumnos
            cursor.execute("""
                SELECT 
                    a.id_alumno as id,
                    a.nombre_alumno as nombre,
                    a.apellido_paterno,
                    a.apellido_materno,
                    a.correo_electronico as correo,
                    a.matricula,
                    a.id_carrera,
                    a.primer_login,
                    c.nombre_carrera,
                    'alumno' as rol
                FROM alumnos a
                LEFT JOIN carreras c ON a.id_carrera = c.id_carrera
                ORDER BY a.id_alumno DESC
            """)
            alumnos = cursor.fetchall()
            
            for alumno in alumnos:
                usuarios.append(dict(alumno))
            
            # Obtener administradores
            cursor.execute("""
                SELECT 
                    id_control as id,
                    nombre_admin as nombre,
                    apellido_paterno,
                    apellido_materno,
                    email as correo,
                    primer_login,
                    'admin' as rol
                FROM administrador
                ORDER BY id_control DESC
            """)
            admins = cursor.fetchall()
            
            for admin in admins:
                usuarios.append(dict(admin))
            
    except Exception as e:
        print(f"Error api_usuarios: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conexion.close()
    
    return jsonify(usuarios)

@app.route('/api/usuarios/<int:id>', methods=['GET'])
def api_usuario_by_id(id):
    """API para obtener un usuario específico"""
    if not session.get('admin_logged') and not session.get('user_tipo') == 'admin':
        return jsonify({'error': 'No autorizado'}), 401
    
    rol = request.args.get('rol')
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            if rol == 'alumno':
                cursor.execute("""
                    SELECT 
                        a.id_alumno as id,
                        a.nombre_alumno as nombre,
                        a.apellido_paterno,
                        a.apellido_materno,
                        a.correo_electronico as correo,
                        a.matricula,
                        a.id_carrera,
                        a.primer_login,
                        c.nombre_carrera,
                        'alumno' as rol
                    FROM alumnos a
                    LEFT JOIN carreras c ON a.id_carrera = c.id_carrera
                    WHERE a.id_alumno = %s
                """, (id,))
            else:
                cursor.execute("""
                    SELECT 
                        id_control as id,
                        nombre_admin as nombre,
                        apellido_paterno,
                        apellido_materno,
                        email as correo,
                        primer_login,
                        'admin' as rol
                    FROM administrador
                    WHERE id_control = %s
                """, (id,))
            
            usuario = cursor.fetchone()
            
            if not usuario:
                return jsonify({'error': 'Usuario no encontrado'}), 404
            
            return jsonify(dict(usuario))
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conexion.close()



@app.route('/api/usuarios/<int:id>', methods=['PUT'])
def api_actualizar_usuario(id):
    """API para actualizar usuario"""
    if not session.get('admin_logged') and not session.get('user_tipo') == 'admin':
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
                sql = """
                    UPDATE alumnos SET
                        nombre_alumno = %s,
                        apellido_paterno = %s,
                        apellido_materno = %s,
                        correo_electronico = %s,
                        matricula = %s,
                        id_carrera = %s
                    WHERE id_alumno = %s
                """
                cursor.execute(sql, (nombre, apellido_paterno, apellido_materno,
                                    correo, matricula, id_carrera, id))
                conexion.commit()
        
        elif rol == 'admin':
            with conexion.cursor() as cursor:
                sql = """
                    UPDATE administrador SET
                        nombre_admin = %s,
                        apellido_paterno = %s,
                        apellido_materno = %s,
                        email = %s
                    WHERE id_control = %s
                """
                cursor.execute(sql, (nombre, apellido_paterno, apellido_materno,
                                    correo, id))
                conexion.commit()
        
        else:
            return jsonify({'success': False, 'message': 'Rol no válido'})
        
        return jsonify({'success': True, 'message': 'Usuario actualizado correctamente'})
        
    except Exception as e:
        conexion.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conexion.close()


@app.route('/api/usuarios/<int:id>', methods=['DELETE'])
def api_eliminar_usuario(id):
    """API para eliminar usuario"""
    if not session.get('admin_logged') and not session.get('user_tipo') == 'admin':
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


@app.route('/admin/usuarios', methods=['GET'])
def admin_usuarios_lista():
    """Página de gestión de usuarios"""
    if not session.get('admin_logged') and not session.get('user_tipo') == 'admin':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('login'))
    
    conexion = config.conectar_db()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_carrera, nombre_carrera FROM carreras")
            carreras = cursor.fetchall()
    except Exception as e:
        print(f"Error: {e}")
        carreras = []
    finally:
        conexion.close()
    
    return render_template('admin_usuarios.html', carreras=carreras)

@app.route('/olvide-password', methods=['GET', 'POST'])
def olvide_password():
    """Solicitar recuperación de contraseña"""
    if request.method == 'POST':
        email = request.form.get('email')
        tipo = request.form.get('tipo', 'alumno')  # Para distinguir si es admin o alumno
        
        if not email:
            flash('Ingresa tu correo electrónico', 'error')
            return redirect(url_for('olvide_password'))
        
        conexion = config.conectar_db()
        usuario = None
        usuario_nombre = None
        usuario_id = None
        rol_detectado = None
        
        try:
            with conexion.cursor() as cursor:
                # Buscar en administradores
                cursor.execute("SELECT * FROM administrador WHERE email = %s", (email,))
                admin = cursor.fetchone()
                
                if admin:
                    usuario_id = admin['id_control']
                    usuario_nombre = admin['nombre_admin']
                    rol_detectado = 'admin'
                else:
                    # Buscar en alumnos
                    cursor.execute("SELECT * FROM alumnos WHERE correo_electronico = %s", (email,))
                    alumno = cursor.fetchone()
                    if alumno:
                        usuario_id = alumno['id_alumno']
                        usuario_nombre = f"{alumno['nombre_alumno']} {alumno['apellido_paterno']}"
                        rol_detectado = 'alumno'
                
                if usuario_id:
                    # Generar token único
                    token = secrets.token_urlsafe(32)
                    fecha_expiracion = datetime.now() + timedelta(hours=24)
                    
                    # Guardar token en tabla (crear tabla si no existe)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS recuperacion_password (
                            id_recuperacion INT AUTO_INCREMENT PRIMARY KEY,
                            usuario_id INT NOT NULL,
                            tipo_usuario ENUM('admin', 'alumno') NOT NULL,
                            token VARCHAR(100) NOT NULL UNIQUE,
                            fecha_solicitud DATETIME DEFAULT CURRENT_TIMESTAMP,
                            fecha_expiracion DATETIME,
                            usado BOOLEAN DEFAULT FALSE
                        )
                    """)
                    
                    cursor.execute("""
                        INSERT INTO recuperacion_password 
                        (usuario_id, tipo_usuario, token, fecha_expiracion)
                        VALUES (%s, %s, %s, %s)
                    """, (usuario_id, rol_detectado, token, fecha_expiracion))
                    conexion.commit()
                    
                    # ✉️ ENVIAR CORREO DE RECUPERACIÓN
                    enviar_enlace_recuperacion(email, usuario_nombre, token, rol_detectado)
                    flash('Se ha enviado un enlace de recuperación a tu correo electrónico.', 'success')
                else:
                    # Por seguridad, no revelar si el correo existe o no
                    flash('Si el correo está registrado, recibirás un enlace de recuperación.', 'info')
                    
        except Exception as e:
            print(f"Error en recuperación: {e}")
            flash('Error al procesar la solicitud', 'error')
        finally:
            conexion.close()
        
        return redirect(url_for('login'))
        
    
    return render_template('olvide_password.html')

@app.route('/cambiar-password', methods=['GET', 'POST'])
def cambiar_password():
    """Cambiar contraseña (primer login o voluntario)"""
    if not session.get('user_id'):
        flash('Debes iniciar sesión primero', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')
        
        if not nueva_password or not confirmar_password:
            flash('Todos los campos son requeridos', 'error')
            return redirect(url_for('cambiar_password'))
        
        if nueva_password != confirmar_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('cambiar_password'))
        
        # ============================================
        # VALIDACIÓN DE CONTRASEÑA FUERTE
        # ============================================
        if len(nueva_password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres', 'error')
            return redirect(url_for('cambiar_password'))
        
        if not re.search(r'[A-Z]', nueva_password):
            flash('La contraseña debe tener al menos una letra mayúscula (A-Z)', 'error')
            return redirect(url_for('cambiar_password'))
        
        if not re.search(r'[a-z]', nueva_password):
            flash('La contraseña debe tener al menos una letra minúscula (a-z)', 'error')
            return redirect(url_for('cambiar_password'))
        
        if not re.search(r'[0-9]', nueva_password):
            flash('La contraseña debe tener al menos un número (0-9)', 'error')
            return redirect(url_for('cambiar_password'))
        
        if not re.search(r'[!@#$%^&*()_\-+=<>?{}[\]~]', nueva_password):
            flash('La contraseña debe tener al menos un carácter especial (!@#$%^&*)', 'error')
            return redirect(url_for('cambiar_password'))
        
        # ============================================
        # FIN VALIDACIÓN
        # ============================================
        
        hashed = generate_password_hash(nueva_password)
        conexion = config.conectar_db()
        
        try:
            with conexion.cursor() as cursor:
                if session['user_tipo'] == 'alumno':
                    cursor.execute("""
                        UPDATE alumnos 
                        SET password = %s, primer_login = FALSE 
                        WHERE id_alumno = %s
                    """, (hashed, session['user_id']))
                else:
                    cursor.execute("""
                        UPDATE administrador 
                        SET password = %s, primer_login = FALSE 
                        WHERE id_control = %s
                    """, (hashed, session['user_id']))
                
                conexion.commit()
                flash('Contraseña actualizada correctamente', 'success')
                
        except Exception as e:
            print(f"Error al cambiar password: {e}")
            flash('Error al cambiar la contraseña', 'error')
            return redirect(url_for('cambiar_password'))
        finally:
            conexion.close()
        
        # Redirigir según el tipo de usuario
        if session['user_tipo'] == 'alumno':
            return redirect(url_for('alumno_dashboard'))
        else:
            return redirect(url_for('admin_dashboard'))
    
    return render_template('cambiar_password.html')

# En alumno_dashboard() de app.py
@app.route('/alumno/dashboard')
def alumno_dashboard():
    if not session.get('user_tipo') == 'alumno':
        return redirect(url_for('login'))
    
    conexion = config.conectar_db()
    evento_publicado = None
    sesiones = []
    
    try:
        with conexion.cursor() as cursor:
            # Obtener evento publicado
            cursor.execute("""
                SELECT * FROM evento 
                WHERE publicado = TRUE AND activo = 1
                ORDER BY fecha_publicacion DESC LIMIT 1
            """)
            evento_publicado = cursor.fetchone()
            
            if evento_publicado:
                # Obtener sesiones de ese evento
                cursor.execute("""
                    SELECT s.*, ts.nombre_sesion as tipo, 
                           e.nombre_escenario as escenario_nombre
                    FROM sesion s
                    JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                    JOIN escenarios e ON s.id_escenario = e.id_escenario
                    WHERE s.id_evento = %s
                    ORDER BY s.fecha, s.hora_inicio
                """, (evento_publicado['id_evento'],))
                sesiones = cursor.fetchall()
    finally:
        conexion.close()
    
    return render_template('alumno_dashboard.html', 
                         evento=evento_publicado,
                         sesiones=sesiones,
                         nombre=session.get('user_nombre'))
# ==================== EVENTOS CRUD ====================

@app.route("/api/eventos", methods=["GET"])
def api_listar_eventos():
    """Lista todos los eventos ordenados por año desc."""
    if not session.get("admin_logged"):
        return jsonify({"error": "No autorizado"}), 401

    con = config.conectar_db()
    if not con:
        return jsonify([]), 500
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT e.*,
                       COUNT(s.id_sesion) AS total_sesiones
                FROM evento e
                LEFT JOIN sesion s ON s.id_evento = e.id_evento
                GROUP BY e.id_evento
                ORDER BY e.anio DESC, e.fecha_inicio DESC
            """)
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for campo in ("fecha_inicio", "fecha_fin", "creado_en", "actualizado_en"):
                if d.get(campo) and hasattr(d[campo], "strftime"):
                    d[campo] = d[campo].strftime(
                        "%Y-%m-%d" if "fecha" in campo else "%Y-%m-%d %H:%M:%S"
                    )
            result.append(d)
        return jsonify(result)
    except Exception as e:
        print(f"[api_listar_eventos] {e}")
        return jsonify([]), 500
    finally:
        con.close()


def _dias_evento(fecha_inicio, fecha_fin):
    """Genera lista de fechas entre fecha_inicio y fecha_fin excluyendo fines de semana."""
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

    dias = []
    current = fecha_inicio
    while current <= fecha_fin:
        if current.weekday() < 5:  # 0=Lun, 4=Vie
            dias.append(current)
        current += timedelta(days=1)
    return dias


@app.route("/api/eventos", methods=["POST"])
def api_crear_evento():
    """Crea un nuevo evento."""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401

    data = request.get_json()
    nombre = (data.get("nombre") or "").strip()
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    descripcion = (data.get("descripcion") or "").strip() or None
    activar = bool(data.get("activar", False))

    if not nombre:
        return jsonify({"success": False, "message": "El nombre del evento es requerido"})
    if not fecha_inicio or not fecha_fin:
        return jsonify({"success": False, "message": "Las fechas son requeridas"})

    try:
        fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Formato de fecha inválido"})

    if ff < fi:
        return jsonify({"success": False, "message": "La fecha fin no puede ser anterior a la fecha inicio"})

    dias_habiles = _dias_evento(fi, ff)
    if not dias_habiles:
        return jsonify({"success": False, "message": "El rango seleccionado no contiene días hábiles (Lun-Vie)"})

    anio = fi.year

    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500

    try:
        with con.cursor() as cur:
            if activar:
                cur.execute("UPDATE evento SET activo = 0")

            cur.execute("""
                INSERT INTO evento (nombre, anio, fecha_inicio, fecha_fin, descripcion, activo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, anio, fi, ff, descripcion, 1 if activar else 0))
            nuevo_id = cur.lastrowid
        con.commit()
        return jsonify({
            "success": True,
            "message": "Evento creado exitosamente",
            "id_evento": nuevo_id,
            "dias_habiles": len(dias_habiles)
        })
    except Exception as e:
        con.rollback()
        print(f"[api_crear_evento] {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()


@app.route("/api/eventos/<int:id_evento>", methods=["PUT"])
def api_editar_evento(id_evento):
    """Edita nombre, fechas y descripción de un evento."""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401

    data = request.get_json()
    nombre = (data.get("nombre") or "").strip()
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    descripcion = (data.get("descripcion") or "").strip() or None

    if not nombre or not fecha_inicio or not fecha_fin:
        return jsonify({"success": False, "message": "Faltan campos requeridos"})

    try:
        fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Formato de fecha inválido"})

    if ff < fi:
        return jsonify({"success": False, "message": "La fecha fin no puede ser anterior a la fecha inicio"})

    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500
    try:
        with con.cursor() as cur:
            cur.execute("""
                UPDATE evento
                SET nombre=%s, anio=%s, fecha_inicio=%s, fecha_fin=%s, descripcion=%s
                WHERE id_evento=%s
            """, (nombre, fi.year, fi, ff, descripcion, id_evento))
        con.commit()
        return jsonify({"success": True, "message": "Evento actualizado"})
    except Exception as e:
        con.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()


@app.route("/api/eventos/<int:id_evento>/activar", methods=["POST"])
def api_activar_evento(id_evento):
    """Marca un evento como activo (desactiva los demás)."""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401

    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500
    try:
        with con.cursor() as cur:
            cur.execute("UPDATE evento SET activo = 0")
            cur.execute("UPDATE evento SET activo = 1 WHERE id_evento = %s", (id_evento,))
        con.commit()
        return jsonify({"success": True, "message": "Evento activado"})
    except Exception as e:
        con.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()


@app.route("/api/eventos/<int:id_evento>", methods=["DELETE"])
def api_eliminar_evento(id_evento):
    """Elimina un evento (sus sesiones quedan con id_evento=NULL)."""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401

    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500
    try:
        with con.cursor() as cur:
            cur.execute("DELETE FROM evento WHERE id_evento = %s", (id_evento,))
        con.commit()
        return jsonify({"success": True, "message": "Evento eliminado"})
    except Exception as e:
        con.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()


# ==================== SESIONES POR EVENTO ====================

@app.route("/api/eventos/<int:id_evento>/sesiones")
def api_sesiones_por_evento(id_evento):
    """Devuelve todas las sesiones de un evento."""
    if not session.get("admin_logged"):
        return jsonify([])

    con = config.conectar_db()
    if not con:
        return jsonify([])

    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT
                    s.id_sesion, s.id_evento, s.sede,
                    s.nombre_de_sesion, s.fecha,
                    s.nombre_ponente, s.apellido_paterno, s.apellido_materno,
                    s.perfil_profesional, s.hora_inicio, s.hora_fin,
                    s.cupo_audiencia, s.fotografia,
                    ts.nombre_sesion AS tipo,
                    e.nombre_escenario AS escenario_nombre,
                    e.id_escenario,
                    c.nombre_carrera AS carrera_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON ts.id_tipo_sesion = s.id_tipo_sesion
                JOIN escenarios e ON e.id_escenario = s.id_escenario
                LEFT JOIN carreras c ON c.id_carrera = s.id_carrera
                WHERE s.id_evento = %s
                ORDER BY s.fecha, s.hora_inicio
            """, (id_evento,))
            sesiones = cur.fetchall()

        result = []
        for s in sesiones:
            item = dict(s)
            # Convertir fecha
            if item.get("fecha") and hasattr(item["fecha"], "strftime"):
                item["fecha"] = item["fecha"].strftime("%Y-%m-%d")
            # Convertir horas
            for campo in ("hora_inicio", "hora_fin"):
                val = item.get(campo)
                if val is not None:
                    if hasattr(val, "seconds"):
                        h = val.seconds // 3600
                        m = (val.seconds % 3600) // 60
                        item[campo] = f"{h:02d}:{m:02d}"
                        item[f"{campo}_str"] = f"{h:02d}:{m:02d}"
                    elif hasattr(val, "strftime"):
                        item[campo] = val.strftime("%H:%M")
                        item[f"{campo}_str"] = val.strftime("%H:%M")
            if item.get("cupo_audiencia") is None:
                item["cupo_audiencia"] = 0
            result.append(item)

        return jsonify(result)
    except Exception as e:
        print(f"[api_sesiones_por_evento] {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])
    finally:
        con.close()


@app.route("/api/eventos/<int:id_evento>/conflictos")
def api_conflictos_evento(id_evento):
    """Devuelve la lista de pares de sesiones en conflicto dentro de un evento."""
    if not session.get("admin_logged"):
        return jsonify([])

    con = config.conectar_db()
    if not con:
        return jsonify([])

    try:
        with con.cursor() as cur:
            # Primero asegurar que la vista existe
            cur.execute("""
                CREATE OR REPLACE VIEW v_conflictos_sesion AS
                SELECT
                    a.id_sesion AS id_sesion_a,
                    b.id_sesion AS id_sesion_b,
                    a.id_evento,
                    a.fecha,
                    a.id_escenario,
                    e.nombre_escenario,
                    a.nombre_de_sesion AS sesion_a,
                    b.nombre_de_sesion AS sesion_b,
                    a.hora_inicio AS inicio_a,
                    a.hora_fin AS fin_a,
                    b.hora_inicio AS inicio_b,
                    b.hora_fin AS fin_b
                FROM sesion a
                JOIN sesion b ON a.id_evento = b.id_evento
                    AND a.fecha = b.fecha
                    AND a.id_escenario = b.id_escenario
                    AND a.id_sesion < b.id_sesion
                JOIN escenarios e ON a.id_escenario = e.id_escenario
                WHERE a.id_evento IS NOT NULL
                  AND NOT (a.hora_fin <= b.hora_inicio OR a.hora_inicio >= b.hora_fin)
            """)

            cur.execute("""
                SELECT
                    vc.*,
                    TIME_FORMAT(vc.inicio_a, '%%H:%%i') AS inicio_a_str,
                    TIME_FORMAT(vc.fin_a, '%%H:%%i') AS fin_a_str,
                    TIME_FORMAT(vc.inicio_b, '%%H:%%i') AS inicio_b_str,
                    TIME_FORMAT(vc.fin_b, '%%H:%%i') AS fin_b_str
                FROM v_conflictos_sesion vc
                WHERE vc.id_evento = %s
            """, (id_evento,))
            rows = cur.fetchall()

        result = []
        for r in rows:
            d = dict(r)
            if d.get("fecha") and hasattr(d["fecha"], "strftime"):
                d["fecha"] = d["fecha"].strftime("%Y-%m-%d")
            result.append(d)
        return jsonify(result)
    except Exception as e:
        print(f"[api_conflictos_evento] {e}")
        return jsonify([])
    finally:
        con.close()


@app.route("/api/eventos/<int:id_evento>/info")
def api_info_evento(id_evento):
    """Devuelve metadata del evento incluyendo días hábiles."""
    if not session.get("admin_logged"):
        return jsonify({"error": "No autorizado"}), 401

    con = config.conectar_db()
    if not con:
        return jsonify({"error": "Sin conexión"}), 500
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM evento WHERE id_evento = %s", (id_evento,))
            ev = cur.fetchone()
        if not ev:
            return jsonify({"error": "No encontrado"}), 404

        d = dict(ev)
        fi = d["fecha_inicio"]
        ff = d["fecha_fin"]
        dias = _dias_evento(fi, ff)

        d["fecha_inicio"] = fi.strftime("%Y-%m-%d") if hasattr(fi, "strftime") else str(fi)
        d["fecha_fin"] = ff.strftime("%Y-%m-%d") if hasattr(ff, "strftime") else str(ff)
        d["dias_habiles"] = [dia.strftime("%Y-%m-%d") for dia in dias]
        d["total_dias"] = len(dias)

        return jsonify(d)
    except Exception as e:
        print(f"[api_info_evento] {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        con.close()


# ==================== EXPORTACIÓN HTML ====================

@app.route("/admin/eventos/<int:id_evento>/exportar-html")
def exportar_itinerario_html(id_evento):
    """Genera una página HTML estática del programa/itinerario del evento."""
    if not session.get("admin_logged"):
        return redirect(url_for("index"))

    con = config.conectar_db()
    if not con:
        flash("Error de conexión", "error")
        return redirect(url_for("admin_sesiones"))

    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM evento WHERE id_evento = %s", (id_evento,))
            ev = cur.fetchone()
            if not ev:
                flash("Evento no encontrado", "error")
                return redirect(url_for("admin_sesiones"))

            cur.execute("""
                SELECT
                    s.*, ts.nombre_sesion AS tipo,
                    e.nombre_escenario AS escenario_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON ts.id_tipo_sesion = s.id_tipo_sesion
                JOIN escenarios e ON e.id_escenario = s.id_escenario
                WHERE s.id_evento = %s
                ORDER BY s.fecha, s.hora_inicio
            """, (id_evento,))
            sesiones = cur.fetchall()

        # Agrupar por fecha
        from collections import defaultdict
        por_dia = defaultdict(list)
        for s in sesiones:
            fecha_str = s["fecha"].strftime("%Y-%m-%d") if hasattr(s["fecha"], "strftime") else str(s["fecha"])
            # Convertir horas
            hora_inicio = s["hora_inicio"]
            hora_fin = s["hora_fin"]
            if hasattr(hora_inicio, "seconds"):
                h = hora_inicio.seconds // 3600
                m = (hora_inicio.seconds % 3600) // 60
                hora_inicio = f"{h:02d}:{m:02d}"
                hora_fin = f"{hora_fin.seconds // 3600:02d}:{(hora_fin.seconds % 3600) // 60:02d}"
            por_dia[fecha_str].append({
                "nombre_de_sesion": s["nombre_de_sesion"],
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
                "tipo": s["tipo"],
                "escenario_nombre": s["escenario_nombre"],
                "nombre_ponente": s["nombre_ponente"],
                "apellido_paterno": s["apellido_paterno"],
            })

        return render_template("itinerario_publico.html",
                               evento=ev,
                               por_dia=dict(por_dia),
                               nombre_evento=ev["nombre"])
    except Exception as e:
        print(f"[exportar_itinerario_html] {e}")
        flash(f"Error al exportar: {e}", "error")
        return redirect(url_for("admin_sesiones"))
    finally:
        con.close()

@app.route("/api/eventos/<int:id_evento>/publicar", methods=["POST"])
def api_publicar_evento(id_evento):
    """Publica u oculta un evento (visible para estudiantes)"""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.get_json()
    publicado = data.get("publicado", False)
    
    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500
    
    try:
        with con.cursor() as cur:
            # Si vamos a publicar este, despublicamos los demás
            if publicado:
                cur.execute("UPDATE evento SET publicado = FALSE")
            
            cur.execute("""
                UPDATE evento 
                SET publicado = %s, fecha_publicacion = %s
                WHERE id_evento = %s
            """, (publicado, datetime.now() if publicado else None, id_evento))
            
        con.commit()
        
        mensaje = "Jornada publicada exitosamente" if publicado else "Jornada ocultada"
        return jsonify({"success": True, "message": mensaje})
    except Exception as e:
        con.rollback()
        print(f"[api_publicar_evento] {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()

@app.route('/admin/verificar_disponibilidad', methods=['POST'])
def verificar_disponibilidad():
    """Verifica si un escenario está disponible en una fecha y horario"""
    try:
        data = request.get_json()
        id_escenario = data.get('id_escenario')
        fecha = data.get('fecha')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        id_sesion_actual = data.get('id_sesion', None)  # Para edición, excluir la sesión actual
        
        if not all([id_escenario, fecha, hora_inicio, hora_fin]):
            return jsonify({'disponible': False, 'mensaje': 'Faltan datos para verificar'})
        
        conexion = config.conectar_db()
        if not conexion:
            return jsonify({'disponible': False, 'mensaje': 'Error de conexión'})
        
        with conexion.cursor() as cursor:
            # Buscar sesiones que ocupen el mismo escenario en el mismo rango horario
            sql = """
                SELECT id_sesion, nombre_de_sesion, hora_inicio, hora_fin
                FROM sesion 
                WHERE id_escenario = %s 
                AND fecha = %s
                AND (
                    (hora_inicio < %s AND hora_fin > %s) OR  -- Superposición parcial
                    (hora_inicio BETWEEN %s AND %s) OR
                    (hora_fin BETWEEN %s AND %s) OR
                    (%s BETWEEN hora_inicio AND hora_fin)
                )
            """
            
            # Si es edición, excluir la sesión actual
            if id_sesion_actual:
                sql += " AND id_sesion != %s"
                params = (id_escenario, fecha, hora_fin, hora_inicio, 
                         hora_inicio, hora_fin, hora_inicio, hora_fin,
                         hora_inicio, id_sesion_actual)
            else:
                params = (id_escenario, fecha, hora_fin, hora_inicio, 
                         hora_inicio, hora_fin, hora_inicio, hora_fin,
                         hora_inicio)
            
            cursor.execute(sql, params)
            conflicto = cursor.fetchone()
            
            if conflicto:
                return jsonify({
                    'disponible': False, 
                    'mensaje': f'El escenario ya está ocupado de {conflicto["hora_inicio"]} a {conflicto["hora_fin"]} por la sesión: "{conflicto["nombre_de_sesion"]}"'
                })
            
            return jsonify({'disponible': True, 'mensaje': 'Escenario disponible'})
            
    except Exception as e:
        print(f"Error al verificar disponibilidad: {e}")
        return jsonify({'disponible': False, 'mensaje': 'Error al verificar disponibilidad'})
    finally:
        if conexion:
            conexion.close()
        
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)