from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail
import config
import os

# Crear app
app = config.app

# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'administradorsesionesumb@gmail.com'
app.config['MAIL_PASSWORD'] = 'qaun eayw roid ebrp'
app.config['MAIL_DEFAULT_SENDER'] = 'administradorsesionesumb@gmail.com'

mail = Mail(app)

# Headers de seguridad
@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    if request.endpoint and ('admin' in request.endpoint or 'alumno' in request.endpoint):
        response.headers['Clear-Site-Data'] = '"cache"'
    return response

# Registrar Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.admin_eventos import admin_eventos_bp
from routes.admin_export import admin_export_bp
from routes.alumno import alumno_bp
from routes.api import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(admin_eventos_bp)
app.register_blueprint(admin_export_bp)
app.register_blueprint(alumno_bp)
app.register_blueprint(api_bp)

# ==================== RUTAS DE COMPATIBILIDAD (PARA QUE LOS TEMPLATES SIGAN FUNCIONANDO) ====================

@app.route('/')
def index():
    return render_template('index.html')

# Estas rutas redirigen a las nuevas
@app.route('/login', methods=['GET', 'POST'])
def login_compat():
    """Compatibilidad para templates que usan url_for('login')"""
    if request.method == 'GET':
        return redirect(url_for('auth.login'))
    else:
        # Redirigir POST también
        return redirect(url_for('auth.login'))

@app.route('/logout')
def logout_compat():
    return redirect(url_for('auth.logout'))

@app.route('/cambiar-password', methods=['GET', 'POST'])
def cambiar_password_compat():
    if request.method == 'GET':
        return redirect(url_for('auth.cambiar_password'))
    else:
        # Redirigir POST a la ruta correcta
        return redirect(url_for('auth.cambiar_password'))

@app.route('/olvide-password', methods=['GET', 'POST'])
def olvide_password_compat():
    if request.method == 'GET':
        return redirect(url_for('auth.olvide_password'))
    else:
        return redirect(url_for('auth.olvide_password'))

@app.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password_compat():
    if request.method == 'GET':
        return redirect(url_for('auth.recuperar_password'))
    else:
        return redirect(url_for('auth.recuperar_password'))

@app.route('/check-session')
def check_session_compat():
    return redirect(url_for('auth.check_session'))

# Redirigir también las rutas POST (para formularios)
@app.route('/login', methods=['POST'])
def login_post_compat():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)