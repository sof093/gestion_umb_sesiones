from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import json
from datetime import datetime
import config
from routes.helpers import formatear_fecha, formatear_hora, enviar_correo_inscripcion

alumno_bp = Blueprint('alumno', __name__, url_prefix='/alumno')

# ==================== DASHBOARD ====================
@alumno_bp.route('/dashboard')
def alumno_dashboard():
    if not session.get('user_tipo') == 'alumno':
        return redirect(url_for('auth.login'))
    
    conexion = config.conectar_db()
    evento_publicado = None
    sesiones = []
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM evento WHERE publicado = TRUE AND activo = 1 ORDER BY fecha_publicacion DESC LIMIT 1")
            evento_publicado = cursor.fetchone()
            
            if evento_publicado:
                cursor.execute("""
                    SELECT s.*, ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre
                    FROM sesion s
                    JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                    JOIN escenarios e ON s.id_escenario = e.id_escenario
                    WHERE s.id_evento = %s
                    ORDER BY s.fecha, s.hora_inicio
                """, (evento_publicado['id_evento'],))
                sesiones_raw = cursor.fetchall()
                
                for sesion in sesiones_raw:
                    sesion_dict = dict(sesion)
                    sesion_dict['fecha_display'] = formatear_fecha(sesion_dict.get('fecha'))
                    
                    hora_inicio = sesion_dict.get('hora_inicio')
                    hora_fin = sesion_dict.get('hora_fin')
                    inicio_str = formatear_hora(hora_inicio)
                    fin_str = formatear_hora(hora_fin)
                    sesion_dict['horario_display'] = f"{inicio_str} – {fin_str}" if inicio_str and fin_str else 'N/A'
                    
                    nombre_parts = filter(None, [sesion_dict.get('nombre_ponente', ''), sesion_dict.get('apellido_paterno', ''), sesion_dict.get('apellido_materno', '')])
                    sesion_dict['nombre_ponente_completo'] = ' '.join(nombre_parts).strip() or 'Ponente no asignado'
                    
                    nombre = sesion_dict.get('nombre_ponente', '')
                    apellido = sesion_dict.get('apellido_paterno', '')
                    sesion_dict['iniciales_ponente'] = (nombre[0] + apellido[0]).upper() if nombre and apellido else nombre[0].upper() if nombre else 'NA'
                    
                    sesiones.append(sesion_dict)
                
                if evento_publicado:
                    evento_dict = dict(evento_publicado)
                    evento_dict['fecha_inicio_display'] = formatear_fecha(evento_dict.get('fecha_inicio'))
                    evento_dict['fecha_fin_display'] = formatear_fecha(evento_dict.get('fecha_fin'))
                    evento_publicado = evento_dict
                    
    except Exception as e:
        print(f"Error en alumno_dashboard: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conexion.close()
    
    sesiones_json_dict = {}
    for s in sesiones:
        sid = str(s.get('id_sesion', ''))
        if sid:
            sesiones_json_dict[sid] = {
                'titulo': s.get('nombre_de_sesion') or 'Sin nombre',
                'tipo': s.get('tipo') or '',
                'ponente': s.get('nombre_ponente_completo') or 'Ponente no asignado',
                'iniciales': s.get('iniciales_ponente') or 'NA',
                'perfil': s.get('perfil_profesional') or '',
                'bio': s.get('biografia') or '',
                'escenario': s.get('escenario_nombre') or 'N/A',
                'cupo': s.get('cupo_audiencia') or 0,
                'fecha': s.get('fecha_display') or 'N/A',
                'horario': s.get('horario_display') or 'N/A'
            }
    
    sesiones_json = json.dumps(sesiones_json_dict, ensure_ascii=False)
    
    return render_template('alumno_dashboard.html', evento=evento_publicado, sesiones=sesiones, sesiones_json=sesiones_json, nombre=session.get('user_nombre'))

# ==================== INSCRIPCIONES ====================
@alumno_bp.route('/inscribir/<int:id_sesion>', methods=['POST'])
def alumno_inscribir(id_sesion):
    if not session.get('user_tipo') == 'alumno':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    id_alumno = session.get('user_id')
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT * FROM inscripciones WHERE id_alumno = %s AND id_sesion = %s", (id_alumno, id_sesion))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Ya estás inscrito'})
            
            cursor.execute("""
                SELECT s.cupo_audiencia, COUNT(i.id_inscripcion) as inscritos
                FROM sesion s
                LEFT JOIN inscripciones i ON s.id_sesion = i.id_sesion
                WHERE s.id_sesion = %s
                GROUP BY s.id_sesion
            """, (id_sesion,))
            resultado = cursor.fetchone()
            if resultado and resultado['cupo_audiencia'] and resultado['inscritos'] >= resultado['cupo_audiencia']:
                return jsonify({'success': False, 'message': 'Cupo lleno'})
            
            cursor.execute("INSERT INTO inscripciones (id_alumno, id_sesion, fecha_inscripcion) VALUES (%s, %s, NOW())", (id_alumno, id_sesion))
            conexion.commit()
            
            cursor.execute("""
                SELECT s.nombre_de_sesion, s.fecha, s.hora_inicio, s.hora_fin, e.nombre_escenario
                FROM sesion s
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                WHERE s.id_sesion = %s
            """, (id_sesion,))
            sesion = cursor.fetchone()
            
            enviar_correo_inscripcion(session.get('user_email'), session.get('user_nombre'), sesion['nombre_de_sesion'], sesion['fecha'], sesion['hora_inicio'], sesion['hora_fin'], sesion['nombre_escenario'])
            
            return jsonify({'success': True, 'message': '✅ Inscripción exitosa'})
    except Exception as e:
        conexion.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conexion.close()

@alumno_bp.route('/desinscribir/<int:id_sesion>', methods=['POST'])
def alumno_desinscribir(id_sesion):
    if not session.get('user_tipo') == 'alumno':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    id_alumno = session.get('user_id')
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM inscripciones WHERE id_alumno = %s AND id_sesion = %s", (id_alumno, id_sesion))
            conexion.commit()
            return jsonify({'success': True, 'message': 'Sesión eliminada de tu agenda'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conexion.close()

# ==================== AGENDA PERSONAL ====================
@alumno_bp.route('/agenda')
def alumno_agenda():
    if not session.get('user_tipo') == 'alumno':
        return redirect(url_for('auth.login'))
    
    id_alumno = session.get('user_id')
    nombre = session.get('user_nombre')
    conexion = config.conectar_db()
    
    evento_nombre = None
    sesiones_inscritas = []
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT nombre FROM evento WHERE publicado = TRUE AND activo = 1 ORDER BY fecha_publicacion DESC LIMIT 1")
            evento = cursor.fetchone()
            if evento:
                evento_nombre = evento['nombre']
            
            cursor.execute("""
                SELECT s.id_sesion, s.nombre_de_sesion, s.fecha, s.hora_inicio, s.hora_fin,
                       s.nombre_ponente, s.apellido_paterno, s.apellido_materno,
                       s.perfil_profesional, s.biografia,
                       ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre
                FROM inscripciones i
                JOIN sesion s ON i.id_sesion = s.id_sesion
                JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                WHERE i.id_alumno = %s
                ORDER BY s.fecha ASC, s.hora_inicio ASC
            """, (id_alumno,))
            
            for sesion in cursor.fetchall():
                sesion_dict = dict(sesion)
                sesion_dict['fecha_display'] = sesion_dict['fecha'].strftime('%d/%m/%Y') if hasattr(sesion_dict.get('fecha'), 'strftime') else 'Sin fecha'
                sesion_dict['fecha_sort'] = sesion_dict['fecha'].strftime('%Y-%m-%d') if hasattr(sesion_dict.get('fecha'), 'strftime') else '9999-12-31'
                
                for campo in ('hora_inicio', 'hora_fin'):
                    val = sesion_dict.get(campo)
                    if val:
                        if hasattr(val, 'strftime'):
                            sesion_dict[campo] = val.strftime('%H:%M')
                        elif hasattr(val, 'seconds'):
                            h = val.seconds // 3600
                            m = (val.seconds % 3600) // 60
                            sesion_dict[campo] = f"{h:02d}:{m:02d}"
                
                nombre_parts = filter(None, [sesion_dict.get('nombre_ponente', ''), sesion_dict.get('apellido_paterno', ''), sesion_dict.get('apellido_materno', '')])
                sesion_dict['ponente'] = ' '.join(nombre_parts).strip() or 'Ponente no asignado'
                
                nombre = sesion_dict.get('nombre_ponente', '')
                apellido = sesion_dict.get('apellido_paterno', '')
                sesion_dict['iniciales'] = (nombre[0] + apellido[0]).upper() if nombre and apellido else nombre[0].upper() if nombre else 'NA'
                
                sesiones_inscritas.append(sesion_dict)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conexion.close()
    
    sesiones_inscritas.sort(key=lambda x: x['fecha_sort'])
    sesiones_json = json.dumps(sesiones_inscritas, default=str, ensure_ascii=False)
    
    return render_template('alumno_agenda.html', sesiones_json=sesiones_json, nombre=nombre, evento_nombre=evento_nombre)

@alumno_bp.route('/inscripciones', methods=['GET'])
def alumno_inscripciones():
    if not session.get('user_tipo') == 'alumno':
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    id_alumno = session.get('user_id')
    conexion = config.conectar_db()
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id_sesion FROM inscripciones WHERE id_alumno = %s", (id_alumno,))
            inscritas = [r['id_sesion'] for r in cursor.fetchall()]
            return jsonify({'success': True, 'inscritas': inscritas})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conexion.close()

@alumno_bp.route('/agenda/exportar-pdf')
def alumno_exportar_pdf():
    """Redirige al endpoint de exportación de PDF con logos"""
    return redirect(url_for('admin_export.alumno_exportar_agenda_pdf'))

# ==================== PONENTES ====================
@alumno_bp.route('/ponentes')
def alumnos_ponentes():
    """Muestra la lista de ponentes que participan en las sesiones del evento activo"""
    if not session.get('user_tipo') == 'alumno':
        return redirect(url_for('auth.login'))
    
    conexion = config.conectar_db()
    evento_publicado = None
    ponentes_lista = []
    
    try:
        with conexion.cursor() as cursor:
            # 1. Obtener el evento activo
            cursor.execute("""
                SELECT * FROM evento 
                WHERE publicado = TRUE AND activo = 1 
                ORDER BY fecha_publicacion DESC 
                LIMIT 1
            """)
            evento_publicado = cursor.fetchone()
            
            if evento_publicado:
                # Formatear fechas del evento
                evento_dict = dict(evento_publicado)
                if evento_dict.get('fecha_inicio'):
                    evento_dict['fecha_inicio_display'] = formatear_fecha(evento_dict['fecha_inicio'])
                if evento_dict.get('fecha_fin'):
                    evento_dict['fecha_fin_display'] = formatear_fecha(evento_dict['fecha_fin'])
                evento_publicado = evento_dict
                
                # 2. Obtener todas las sesiones del evento con datos de ponente
                cursor.execute("""
                    SELECT s.*, ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre
                    FROM sesion s
                    JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                    JOIN escenarios e ON s.id_escenario = e.id_escenario
                    WHERE s.id_evento = %s
                    ORDER BY s.fecha, s.hora_inicio
                """, (evento_publicado['id_evento'],))
                sesiones_evento = cursor.fetchall()
                
                # 3. Extraer ponentes ÚNICOS basados en nombre completo
                ponentes_dict = {}
                
                for sesion in sesiones_evento:
                    # Obtener nombre completo del ponente
                    nombre_ponente = sesion.get('nombre_ponente', '').strip()
                    apellido_paterno = sesion.get('apellido_paterno', '').strip()
                    apellido_materno = sesion.get('apellido_materno', '').strip()
                    
                    # Si no hay nombre de ponente, saltar
                    if not nombre_ponente:
                        continue
                    
                    # Crear clave única basada en nombre completo
                    nombre_completo = f"{nombre_ponente} {apellido_paterno} {apellido_materno}".strip()
                    clave_ponente = nombre_completo.lower().replace(' ', '_')
                    
                    if clave_ponente not in ponentes_dict:
                        # Obtener TODAS las sesiones de este mismo ponente en el evento
                        # (buscando por coincidencia de nombre)
                        cursor.execute("""
                            SELECT s.id_sesion, s.nombre_de_sesion, s.fecha, s.hora_inicio, s.hora_fin,
                                   ts.nombre_sesion as tipo_nombre, e.nombre_escenario,
                                   s.nombre_ponente, s.apellido_paterno, s.apellido_materno,
                                   s.perfil_profesional, s.biografia, s.fotografia
                            FROM sesion s
                            JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                            JOIN escenarios e ON s.id_escenario = e.id_escenario
                            WHERE s.id_evento = %s 
                              AND s.nombre_ponente = %s
                              AND s.apellido_paterno <=> %s
                              AND s.apellido_materno <=> %s
                            ORDER BY s.fecha, s.hora_inicio
                        """, (evento_publicado['id_evento'], nombre_ponente, apellido_paterno, apellido_materno))
                        
                        sesiones_ponente = []
                        for sesion_pon in cursor.fetchall():
                            sesion_dict = {
                                'id_sesion': sesion_pon['id_sesion'],
                                'nombre_de_sesion': sesion_pon['nombre_de_sesion'],
                                'tipo': sesion_pon.get('tipo_nombre', 'Sesión'),
                                'fecha': sesion_pon['fecha'],
                                'hora_inicio': sesion_pon['hora_inicio'],
                                'hora_fin': sesion_pon['hora_fin'],
                                'escenario': sesion_pon['nombre_escenario']
                            }
                            # Formatear fecha y hora
                            if sesion_dict['fecha']:
                                sesion_dict['fecha_display'] = formatear_fecha(sesion_dict['fecha'])
                            if sesion_dict['hora_inicio']:
                                sesion_dict['hora_display'] = formatear_hora(sesion_dict['hora_inicio'])
                            sesiones_ponente.append(sesion_dict)
                        
                        # Crear objeto ponente
                        ponente_dict = {
                            'id_ponente': clave_ponente,  # Usar clave única como ID
                            'nombre_ponente': nombre_ponente,
                            'apellido_paterno': apellido_paterno,
                            'apellido_materno': apellido_materno,
                            'perfil_profesional': sesion.get('perfil_profesional', ''),
                            'biografia': sesion.get('biografia', ''),
                            'fotografia': sesion.get('fotografia', ''),
                            'sesiones_asociadas': sesiones_ponente
                        }
                        
                        # Nombre completo para mostrar
                        nombre_parts = filter(None, [nombre_ponente, apellido_paterno, apellido_materno])
                        ponente_dict['nombre_completo'] = ' '.join(nombre_parts).strip()
                        
                        # Iniciales para avatar
                        iniciales = (nombre_ponente[0] if nombre_ponente else '')
                        if apellido_paterno:
                            iniciales += apellido_paterno[0]
                        ponente_dict['iniciales'] = iniciales.upper() if iniciales else 'P'
                        
                        ponentes_dict[clave_ponente] = ponente_dict
                
                # Convertir diccionario a lista para el template
                ponentes_lista = list(ponentes_dict.values())
                
                print(f"📊 Ponentes encontrados: {len(ponentes_lista)}")  # Debug
                
    except Exception as e:
        print(f"❌ Error en alumnos_ponentes: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conexion.close()
    
    return render_template('alumnos_ponentes.html', 
                         evento=evento_publicado,
                         ponentes=ponentes_lista,
                         nombre=session.get('user_nombre', 'Alumno'))