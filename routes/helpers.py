from flask import jsonify
from datetime import datetime, date, timedelta
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import secrets
import config

# ==================== FUNCIONES DE VALIDACIÓN ====================
def validar_solo_letras(texto):
    if not texto:
        return True
    return bool(re.match(r'^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$', texto))

def validar_numero_positivo(valor):
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
    
    return hora_a_minutos(hora_inicio) < hora_a_minutos(hora_fin)

def validar_fecha_no_pasada(fecha_str):
    if not fecha_str:
        return True
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        return fecha >= date.today()
    except:
        return False

# ==================== FUNCIONES DE FORMATEO ====================
def formatear_fecha(valor, formato='%d/%m/%Y'):
    if valor is None:
        return 'N/A'
    if hasattr(valor, 'strftime'):
        return valor.strftime(formato)
    return str(valor)

def formatear_hora(valor):
    if valor is None:
        return None
    if hasattr(valor, 'strftime'):
        return valor.strftime('%I:%M %p')
    if isinstance(valor, timedelta):
        total_seconds = valor.seconds
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return str(valor)

def convertir_hora_para_input(valor):
    if valor is None:
        return None
    if hasattr(valor, 'strftime'):
        return valor.strftime('%H:%M')
    if isinstance(valor, timedelta):
        hours = valor.seconds // 3600
        minutes = (valor.seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return str(valor)[:5] if valor else None

# ==================== FUNCIONES DE CORREO ====================
def enviar_correo(destinatario, asunto, cuerpo_html, cuerpo_texto=None):
    """Función genérica para enviar correos"""
    from flask import current_app
    from flask_mail import Message
    
    mail = current_app.extensions.get('mail')
    if not mail:
        print("Mail no inicializado")
        return False
    
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
    from flask import url_for
    
    asunto = f"Bienvenido al Sistema de Gestión UES - Credenciales de acceso"
    
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #1a3a2a;">Bienvenido al Sistema</h2>
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Se ha creado tu cuenta como <strong>{'Administrador' if rol == 'admin' else 'Alumno'}</strong>.</p>
        <p><strong>Correo:</strong> {email}</p>
        <p><strong>Contraseña temporal:</strong> <code>{password_temporal}</code></p>
        <p>⚠️ Debes cambiar tu contraseña al iniciar sesión.</p>
        <a href="http://localhost:5000/login" style="background: #1a3a2a; color: white; padding: 10px; text-decoration: none;">Iniciar sesión</a>
    </body>
    </html>
    """
    
    return enviar_correo(email, asunto, cuerpo_html)

def enviar_enlace_recuperacion(email, nombre, token, tipo_usuario):
    enlace = f"http://localhost:5000/recuperar-password?token={token}&tipo={tipo_usuario}"
    
    asunto = "Recuperación de contraseña - UES San José del Rincón"
    
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #1a3a2a;">Recuperación de contraseña</h2>
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Haz clic para restablecer tu contraseña:</p>
        <a href="{enlace}" style="background: #1a3a2a; color: white; padding: 10px;">Restablecer</a>
        <p>Este enlace expira en 24 horas.</p>
    </body>
    </html>
    """
    
    return enviar_correo(email, asunto, cuerpo_html)

def enviar_correo_inscripcion(email, nombre_alumno, nombre_sesion, fecha, hora_inicio, hora_fin, escenario):
    asunto = f"Confirmación de inscripción - {nombre_sesion}"
    
    fecha_str = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else str(fecha)
    hora_inicio_str = hora_inicio.strftime('%H:%M') if hasattr(hora_inicio, 'strftime') else str(hora_inicio)
    hora_fin_str = hora_fin.strftime('%H:%M') if hasattr(hora_fin, 'strftime') else str(hora_fin)
    
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #1a3a2a;">Confirmación de inscripción</h2>
        <p>Hola <strong>{nombre_alumno}</strong>,</p>
        <p>Te has inscrito a:</p>
        <p><strong>{nombre_sesion}</strong><br>
        📅 {fecha_str}<br>
        🕐 {hora_inicio_str} - {hora_fin_str}<br>
        📍 {escenario}</p>
        <p>¡Te esperamos!</p>
    </body>
    </html>
    """
    
    return enviar_correo(email, asunto, cuerpo_html)