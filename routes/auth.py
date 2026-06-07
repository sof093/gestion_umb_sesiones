from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import re
import config
from routes.helpers import validar_solo_letras, validar_numero_positivo, validar_horas, validar_fecha_no_pasada, enviar_enlace_recuperacion

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('index.html')
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not email or not password:
        flash('Todos los campos son requeridos', 'error')
        return redirect(url_for('auth.login'))
    
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            # Buscar en administradores
            cursor.execute("SELECT * FROM administrador WHERE email = %s", (email,))
            admin = cursor.fetchone()
            
            if admin and check_password_hash(admin['password'], password):
                session.clear()
                session['user_id'] = admin['id_control']
                session['user_nombre'] = admin['nombre_admin']
                session['user_email'] = admin['email']
                session['user_tipo'] = 'admin'
                session['admin_logged'] = True
                
                if admin.get('primer_login', True):
                    flash('Es tu primer inicio de sesión. Debes cambiar tu contraseña.', 'warning')
                    return redirect(url_for('auth.cambiar_password'))
                
                flash(f'Bienvenido Administrador {admin["nombre_admin"]}', 'success')
                return redirect(url_for('admin.admin_dashboard'))
            
            # Buscar en alumnos
            cursor.execute("SELECT * FROM alumnos WHERE correo_electronico = %s", (email,))
            alumno = cursor.fetchone()
            
            if alumno and check_password_hash(alumno['password'], password):
                session.clear()
                session['user_id'] = alumno['id_alumno']
                session['user_nombre'] = f"{alumno['nombre_alumno']} {alumno['apellido_paterno']}"
                session['user_email'] = alumno['correo_electronico']
                session['user_tipo'] = 'alumno'
                
                if alumno.get('primer_login', True):
                    flash('Es tu primer inicio de sesión. Debes cambiar tu contraseña.', 'warning')
                    return redirect(url_for('auth.cambiar_password'))
                
                flash(f'Bienvenido {alumno["nombre_alumno"]}', 'success')
                return redirect(url_for('alumno.alumno_dashboard'))
            
            flash('Credenciales incorrectas', 'error')
            
    except Exception as e:
        print(f"Error en login: {e}")
        flash('Error al iniciar sesión', 'error')
    finally:
        conexion.close()
    
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    response = redirect(url_for('auth.login'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    flash('Sesión cerrada correctamente', 'info')
    return response

@auth_bp.route('/cambiar-password', methods=['GET', 'POST'])
def cambiar_password():
    if not session.get('user_id'):
        flash('Debes iniciar sesión primero', 'warning')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')
        
        if not nueva_password or not confirmar_password:
            flash('Todos los campos son requeridos', 'error')
            return redirect(url_for('auth.cambiar_password'))
        
        if nueva_password != confirmar_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('auth.cambiar_password'))
        
        # Validación de contraseña fuerte
        if len(nueva_password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres', 'error')
            return redirect(url_for('auth.cambiar_password'))
        
        if not re.search(r'[A-Z]', nueva_password):
            flash('La contraseña debe tener al menos una mayúscula', 'error')
            return redirect(url_for('auth.cambiar_password'))
        
        if not re.search(r'[0-9]', nueva_password):
            flash('La contraseña debe tener al menos un número', 'error')
            return redirect(url_for('auth.cambiar_password'))
        
        if not re.search(r'[!@#$%^&*()_\-+=<>?{}[\]~]', nueva_password):
            flash('La contraseña debe tener al menos un carácter especial', 'error')
            return redirect(url_for('auth.cambiar_password'))
        
        hashed = generate_password_hash(nueva_password)
        conexion = config.conectar_db()
        
        try:
            with conexion.cursor() as cursor:
                if session['user_tipo'] == 'alumno':
                    cursor.execute("UPDATE alumnos SET password = %s, primer_login = FALSE WHERE id_alumno = %s", (hashed, session['user_id']))
                else:
                    cursor.execute("UPDATE administrador SET password = %s, primer_login = FALSE WHERE id_control = %s", (hashed, session['user_id']))
                conexion.commit()
                flash('Contraseña actualizada correctamente', 'success')
        except Exception as e:
            print(f"Error: {e}")
            flash('Error al cambiar la contraseña', 'error')
            return redirect(url_for('auth.cambiar_password'))
        finally:
            conexion.close()
        
        if session['user_tipo'] == 'alumno':
            return redirect(url_for('alumno.alumno_dashboard'))
        else:
            return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('cambiar_password.html')

@auth_bp.route('/olvide-password', methods=['GET', 'POST'])
def olvide_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Ingresa tu correo electrónico', 'error')
            return redirect(url_for('auth.olvide_password'))
        
        conexion = config.conectar_db()
        usuario_id = None
        usuario_nombre = None
        rol_detectado = None
        
        try:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT * FROM administrador WHERE email = %s", (email,))
                admin = cursor.fetchone()
                
                if admin:
                    usuario_id = admin['id_control']
                    usuario_nombre = admin['nombre_admin']
                    rol_detectado = 'admin'
                else:
                    cursor.execute("SELECT * FROM alumnos WHERE correo_electronico = %s", (email,))
                    alumno = cursor.fetchone()
                    if alumno:
                        usuario_id = alumno['id_alumno']
                        usuario_nombre = f"{alumno['nombre_alumno']} {alumno['apellido_paterno']}"
                        rol_detectado = 'alumno'
                
                if usuario_id:
                    token = secrets.token_urlsafe(32)
                    fecha_expiracion = datetime.now() + timedelta(hours=24)
                    
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
                        INSERT INTO recuperacion_password (usuario_id, tipo_usuario, token, fecha_expiracion)
                        VALUES (%s, %s, %s, %s)
                    """, (usuario_id, rol_detectado, token, fecha_expiracion))
                    conexion.commit()
                    
                    enviar_enlace_recuperacion(email, usuario_nombre, token, rol_detectado)
                    flash('Se ha enviado un enlace de recuperación a tu correo.', 'success')
                else:
                    flash('Si el correo está registrado, recibirás un enlace.', 'info')
                    
        except Exception as e:
            print(f"Error: {e}")
            flash('Error al procesar la solicitud', 'error')
        finally:
            conexion.close()
        
        return redirect(url_for('auth.login'))
    
    return render_template('olvide_password.html')

@auth_bp.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'GET':
        token = request.args.get('token')
        tipo = request.args.get('tipo')
        
        if not token or not tipo:
            flash('Enlace inválido', 'error')
            return redirect(url_for('auth.login'))
        
        conexion = config.conectar_db()
        try:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM recuperacion_password 
                    WHERE token = %s AND tipo_usuario = %s AND usado = FALSE AND fecha_expiracion > NOW()
                """, (token, tipo))
                if not cursor.fetchone():
                    flash('El enlace ha expirado o ya fue utilizado', 'error')
                    return redirect(url_for('auth.login'))
            return render_template('recuperar_password.html', token=token, tipo=tipo)
        except Exception as e:
            print(f"Error: {e}")
            flash('Error al verificar el enlace', 'error')
            return redirect(url_for('auth.login'))
        finally:
            conexion.close()
    
    else:  # POST
        token = request.form.get('token')
        tipo = request.form.get('tipo')
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')
        
        if not token or not tipo or not nueva_password or not confirmar_password:
            flash('Datos inválidos', 'error')
            return redirect(url_for('auth.recuperar_password', token=token, tipo=tipo))
        
        if nueva_password != confirmar_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('auth.recuperar_password', token=token, tipo=tipo))
        
        # Validaciones de contraseña (igual que en cambiar_password)
        if len(nueva_password) < 8 or not re.search(r'[A-Z]', nueva_password) or not re.search(r'[0-9]', nueva_password) or not re.search(r'[!@#$%^&*]', nueva_password):
            flash('La contraseña no cumple con los requisitos de seguridad', 'error')
            return redirect(url_for('auth.recuperar_password', token=token, tipo=tipo))
        
        hashed = generate_password_hash(nueva_password)
        conexion = config.conectar_db()
        
        try:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT usuario_id, tipo_usuario FROM recuperacion_password WHERE token = %s AND usado = FALSE", (token,))
                recuperacion = cursor.fetchone()
                
                if not recuperacion:
                    flash('Token inválido', 'error')
                    return redirect(url_for('auth.login'))
                
                if recuperacion['tipo_usuario'] == 'alumno':
                    cursor.execute("UPDATE alumnos SET password = %s, primer_login = FALSE WHERE id_alumno = %s", (hashed, recuperacion['usuario_id']))
                else:
                    cursor.execute("UPDATE administrador SET password = %s, primer_login = FALSE WHERE id_control = %s", (hashed, recuperacion['usuario_id']))
                
                cursor.execute("UPDATE recuperacion_password SET usado = TRUE WHERE token = %s", (token,))
                conexion.commit()
                
                flash('Contraseña restablecida exitosamente', 'success')
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            conexion.rollback()
            print(f"Error: {e}")
            flash('Error al restablecer la contraseña', 'error')
            return redirect(url_for('auth.login'))
        finally:
            conexion.close()

@auth_bp.route('/check-session')
def check_session():
    response = jsonify({'authenticated': False})
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    
    if session.get('user_id') and session.get('user_tipo'):
        response = jsonify({
            'authenticated': True,
            'user_id': session['user_id'],
            'user_tipo': session['user_tipo'],
            'user_nombre': session.get('user_nombre', '')
        })
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        return response
    
    return response, 401