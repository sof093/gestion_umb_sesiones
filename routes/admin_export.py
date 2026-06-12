from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, jsonify
from datetime import datetime
from collections import defaultdict
import os
import json
import time
from io import BytesIO
import config

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image, Paragraph, PageTemplate, BaseDocTemplate, Frame, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas

admin_export_bp = Blueprint('admin_export', __name__, url_prefix='/admin')

# Agrega estas funciones al inicio del archivo admin_export.py

def guardar_configuracion_logos(evento_id, logos_pie=None, logo_izquierda=None, logo_centro=None, logo_derecha=None):
    """Guarda la configuración de logos para un evento"""
    con = config.conectar_db()
    if not con:
        return False
    
    try:
        with con.cursor() as cur:
            # Obtener configuración actual
            cur.execute("SELECT logos_config FROM evento WHERE id_evento = %s", (evento_id,))
            result = cur.fetchone()
            config_data = json.loads(result['logos_config']) if result and result['logos_config'] else {}
            
            # Actualizar valores
            if logos_pie is not None:
                config_data['logos_pie'] = logos_pie
            if logo_izquierda is not None:
                config_data['logo_izquierda'] = logo_izquierda
            if logo_centro is not None:
                config_data['logo_centro'] = logo_centro
            if logo_derecha is not None:
                config_data['logo_derecha'] = logo_derecha
            
            # Guardar
            cur.execute(
                "UPDATE evento SET logos_config = %s WHERE id_evento = %s",
                (json.dumps(config_data), evento_id)
            )
            con.commit()
            return True
    except Exception as e:
        print(f"Error guardando configuración de logos: {e}")
        return False
    finally:
        con.close()

def cargar_configuracion_logos(evento_id):
    """Carga la configuración de logos guardada para un evento"""
    con = config.conectar_db()
    if not con:
        return None
    
    try:
        with con.cursor() as cur:
            cur.execute("SELECT logos_config FROM evento WHERE id_evento = %s", (evento_id,))
            result = cur.fetchone()
            if result and result['logos_config']:
                return json.loads(result['logos_config'])
            return None
    except Exception as e:
        print(f"Error cargando configuración de logos: {e}")
        return None
    finally:
        con.close()


def cargar_logos_desde_configuracion(evento_id, max_ancho=None, max_alto=None):
    """
    Carga los logos según la configuración guardada del evento
    Retorna: (logo_izquierda, logo_centro, logo_derecha, logos_pie)
    """
    config = cargar_configuracion_logos(evento_id)
    if not config:
        return None, None, None, []
    
    # Cargar logos del encabezado
    logo_izq = None
    logo_cent = None
    logo_der = None
    
    if max_ancho and max_alto:
        # Si se especifican dimensiones, cargar proporcionalmente
        if config.get('logo_izquierda'):
            logo_izq = cargar_imagen_proporcional(config['logo_izquierda'], max_ancho, max_alto)
        if config.get('logo_centro'):
            logo_cent = cargar_imagen_proporcional(config['logo_centro'], max_ancho, max_alto)
        if config.get('logo_derecha'):
            logo_der = cargar_imagen_proporcional(config['logo_derecha'], max_ancho, max_alto)
    else:
        # Carga normal
        if config.get('logo_izquierda'):
            logo_izq = cargar_imagen(config['logo_izquierda'], 55, 50)
        if config.get('logo_centro'):
            logo_cent = cargar_imagen(config['logo_centro'], 55, 50)
        if config.get('logo_derecha'):
            logo_der = cargar_imagen(config['logo_derecha'], 55, 50)
    
    # Cargar logos del pie
    logos_pie = []
    if config.get('logos_pie') and max_ancho and max_alto:
        for logo_path in config['logos_pie']:
            logo = cargar_imagen_proporcional(logo_path, max_ancho, max_alto)
            if logo:
                logos_pie.append(logo)
    elif config.get('logos_pie'):
        # Si no hay dimensiones, cargar normalmente (mantener compatibilidad)
        for logo_path in config['logos_pie']:
            logo = cargar_imagen(logo_path, 50, 50)
            if logo:
                logos_pie.append(logo)
    
    return logo_izq, logo_cent, logo_der, logos_pie

def cargar_imagen(ruta, ancho=50, alto=50):
    """Carga una imagen preservando proporciones dentro de los límites dados."""
    if not ruta:
        return None
    try:
        ruta_limpia = ruta.replace('\\', '/')
        rutas_posibles = [
            ruta_limpia,
            ruta_limpia.lstrip('/'),
            os.path.join('static', ruta_limpia.lstrip('/')),
            os.path.join('static/img', os.path.basename(ruta_limpia)),
            os.path.join('static/uploads/sesiones', os.path.basename(ruta_limpia))
        ]
        
        for ruta_intento in rutas_posibles:
            if os.path.exists(ruta_intento):
                print(f"✅ Imagen encontrada: {ruta_intento}")
                img = Image(ruta_intento, width=ancho, height=alto, mask='auto')
                return img
        
        print(f"⚠️ Imagen no encontrada: {ruta}")
        return None
    except Exception as e:
        print(f"❌ Error cargando imagen {ruta}: {e}")
        return None


def cargar_imagen_proporcional(ruta, max_ancho, max_alto):
    """
    Carga una imagen y la escala proporcionalmente para que quepa en max_ancho x max_alto
    sin deformarla.
    """
    if not ruta:
        return None
    try:
        ruta_limpia = ruta.replace('\\', '/')
        rutas_posibles = [
            ruta_limpia,
            ruta_limpia.lstrip('/'),
            os.path.join('static', ruta_limpia.lstrip('/')),
            os.path.join('static/img', os.path.basename(ruta_limpia)),
            os.path.join('static/uploads/sesiones', os.path.basename(ruta_limpia))
        ]

        ruta_encontrada = None
        for ruta_intento in rutas_posibles:
            if os.path.exists(ruta_intento):
                ruta_encontrada = ruta_intento
                break

        if not ruta_encontrada:
            print(f"⚠️ Imagen no encontrada: {ruta}")
            return None

        # Obtener dimensiones reales de la imagen
        try:
            from PIL import Image as PILImage
            with PILImage.open(ruta_encontrada) as pil_img:
                img_w, img_h = pil_img.size
        except Exception:
            # Si PIL no está disponible, usar tamaño máximo directamente
            img = Image(ruta_encontrada, width=max_ancho, height=max_alto, mask='auto')
            return img

        # Calcular escala proporcional
        escala_w = max_ancho / img_w
        escala_h = max_alto / img_h
        escala = min(escala_w, escala_h)

        nuevo_ancho = img_w * escala
        nuevo_alto = img_h * escala

        img = Image(ruta_encontrada, width=nuevo_ancho, height=nuevo_alto, mask='auto')
        print(f"✅ Imagen cargada proporcional: {ruta_encontrada} → {nuevo_ancho:.1f}x{nuevo_alto:.1f}")
        return img

    except Exception as e:
        print(f"❌ Error cargando imagen proporcional {ruta}: {e}")
        return None

@admin_export_bp.route("/eventos/guardar-configuracion", methods=['POST'])
def guardar_configuracion():
    """Guarda solo la configuración de logos sin generar PDF"""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    evento_id = request.form.get('evento_id')
    logos_pie_json = request.form.get('logos_pie', '[]')
    
    if not evento_id:
        return jsonify({"success": False, "message": "ID de evento requerido"}), 400
    
    try:
        logos_pie = json.loads(logos_pie_json)
    except Exception:
        logos_pie = []
    
    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500
    
    try:
        # Guardar logos del encabezado
        temp_dir = os.path.join('static', 'temp_logos')
        os.makedirs(temp_dir, exist_ok=True)
        
        saved_logo_paths = {'izquierda': None, 'centro': None, 'derecha': None}
        
        for position in ['izquierda', 'centro', 'derecha']:
            if f'logo_{position}' in request.files:
                file = request.files[f'logo_{position}']
                if file and file.filename:
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"evento_logo_{position}_{evento_id}.{ext}"
                    filepath = os.path.join(temp_dir, filename)
                    file.save(filepath)
                    saved_logo_paths[position] = f"static/temp_logos/{filename}"
                    print(f"✅ Logo {position} guardado permanentemente en: {filepath}")
        
        # Guardar configuración completa
        guardar_configuracion_logos(
            evento_id, 
            logos_pie=logos_pie,
            logo_izquierda=saved_logo_paths['izquierda'],
            logo_centro=saved_logo_paths['centro'],
            logo_derecha=saved_logo_paths['derecha']
        )
        
        return jsonify({
            "success": True, 
            "message": "✅ Configuración guardada correctamente. Los alumnos ahora verán estos logos en sus PDFs."
        })
        
    except Exception as e:
        print(f"Error guardando configuración: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()

@admin_export_bp.route("/eventos/exportar-pdf-personalizado", methods=['POST'])
def exportar_pdf_personalizado():
    """Genera PDF con logos personalizados subidos por el admin y guarda la configuración"""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    evento_id = request.form.get('evento_id')
    logos_pie_json = request.form.get('logos_pie', '[]')
    guardar_como_default = request.form.get('guardar_como_default', 'false') == 'true'  # Nuevo parámetro
    
    if not evento_id:
        return jsonify({"success": False, "message": "ID de evento requerido"}), 400
    
    try:
        logos_pie = json.loads(logos_pie_json)
    except Exception:
        logos_pie = []
    
    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500
    
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM evento WHERE id_evento = %s", (evento_id,))
            ev = cur.fetchone()
            if not ev:
                return jsonify({"success": False, "message": "Evento no encontrado"}), 404
            
            cur.execute("""
                SELECT s.*, ts.nombre_sesion AS tipo, e.nombre_escenario AS escenario_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON ts.id_tipo_sesion = s.id_tipo_sesion
                JOIN escenarios e ON e.id_escenario = s.id_escenario
                WHERE s.id_evento = %s
                ORDER BY s.fecha, s.hora_inicio
            """, (evento_id,))
            sesiones = cur.fetchall()
        
        # Guardar logos del encabezado temporalmente
        temp_dir = os.path.join('static', 'temp_logos')
        os.makedirs(temp_dir, exist_ok=True)
        
        logo_paths = {'izquierda': None, 'centro': None, 'derecha': None}
        saved_logo_paths = {'izquierda': None, 'centro': None, 'derecha': None}  # Para guardar permanentemente
        
        for position in ['izquierda', 'centro', 'derecha']:
            if f'logo_{position}' in request.files:
                file = request.files[f'logo_{position}']
                if file and file.filename:
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    # Usar nombre permanente si se va a guardar
                    if guardar_como_default:
                        filename = f"evento_logo_{position}_{evento_id}.{ext}"
                    else:
                        filename = f"temp_{position}_{evento_id}_{int(time.time())}.{ext}"
                    filepath = os.path.join(temp_dir, filename)
                    file.save(filepath)
                    logo_paths[position] = filepath
                    saved_logo_paths[position] = f"static/temp_logos/{filename}"
                    print(f"✅ Logo {position} guardado en: {filepath}")
        
        # Si se debe guardar como configuración por defecto
        if guardar_como_default:
            # Guardar paths de logos del encabezado
            header_logos = {
                'logo_izquierda': saved_logo_paths['izquierda'],
                'logo_centro': saved_logo_paths['centro'],
                'logo_derecha': saved_logo_paths['derecha']
            }
            # Guardar configuración completa
            guardar_configuracion_logos(
                evento_id, 
                logos_pie=logos_pie,
                logo_izquierda=saved_logo_paths['izquierda'],
                logo_centro=saved_logo_paths['centro'],
                logo_derecha=saved_logo_paths['derecha']
            )
            print(f"✅ Configuración guardada para evento {evento_id}")
        
        # Cargar logos del pie con proporciones correctas
        logos_participantes = []
        max_ancho_logo = 0.55 * inch
        max_alto_logo = 0.45 * inch

        print(f"🔍 Procesando {len(logos_pie)} logos seleccionados para el pie")
        for logo_path in logos_pie:
            # Resolver ruta real del archivo
            full_path = None
            candidatos = [
                logo_path,
                os.path.join('static', logo_path.lstrip('/')),
                os.path.join('static/uploads/sesiones', os.path.basename(logo_path))
            ]
            for c in candidatos:
                if os.path.exists(c):
                    full_path = c
                    break

            if full_path:
                img = cargar_imagen_proporcional(full_path, max_ancho_logo, max_alto_logo)
                if img:
                    logos_participantes.append(img)
                    print(f"    ✅ Logo cargado: {full_path}")
            else:
                print(f"    ❌ No encontrado: {logo_path}")
        
        print(f"📊 Total logos en pie: {len(logos_participantes)}")
        
        pdf_bytes = generar_pdf_con_logos_personalizados(
            ev, sesiones,
            logo_paths['izquierda'],
            logo_paths['centro'],
            logo_paths['derecha'],
            logos_participantes
        )
        
        # Limpiar temporales (solo los que son temporales, no los guardados)
        for position, path in logo_paths.items():
            if path and os.path.exists(path) and not guardar_como_default:
                os.remove(path)
                print(f"🗑️ Eliminado temporal: {path}")
        
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = (
            f'attachment; filename="itinerario_{ev["nombre"].replace(" ", "_")}_personalizado.pdf"'
        )
        return response
        
    except Exception as e:
        print(f"Error generando PDF personalizado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()

def _dibujar_logos_pie(canvas_obj, logos_participantes, ancho_pagina, y_base):
    """Dibuja los logos del pie de forma centrada y proporcional."""
    if not logos_participantes:
        return

    max_ancho_logo = 0.55 * inch
    max_alto_logo = 0.45 * inch
    espacio = 0.12 * inch
    logos_por_fila = 6

    num_filas = (len(logos_participantes) + logos_por_fila - 1) // logos_por_fila
    y_inicial = y_base - 0.65 * inch
    alto_fila = max_alto_logo + 0.08 * inch

    for fila in range(num_filas):
        inicio = fila * logos_por_fila
        fin = min(inicio + logos_por_fila, len(logos_participantes))
        logos_fila = logos_participantes[inicio:fin]

        # Calcular ancho real de esta fila (logos ya tienen dimensiones proporcionales)
        ancho_total_fila = sum(lg.drawWidth for lg in logos_fila) + (len(logos_fila) - 1) * espacio
        inicio_x = (ancho_pagina - ancho_total_fila) / 2

        x_cursor = inicio_x
        y_logo = y_inicial - (fila * alto_fila)

        for logo_img in logos_fila:
            # Centrar verticalmente dentro del alto de fila
            y_centrado = y_logo + (max_alto_logo - logo_img.drawHeight) / 2
            logo_img.drawOn(canvas_obj, x_cursor, y_centrado)
            x_cursor += logo_img.drawWidth + espacio


def _construir_elementos_tabla(sesiones, COLOR_VERDE, COLOR_VERDE_OSCURO, COLOR_VERDE_CLARO, COLOR_BORDE):
    """
    Construye la lista de elementos Platypus para el contenido del PDF.
    Agrupa título de fecha + tabla en KeepTogether para evitar títulos huérfanos.
    """
    styles = getSampleStyleSheet()
    fecha_style = ParagraphStyle(
        'FechaStyle', parent=styles['Heading3'],
        fontSize=12, textColor=COLOR_VERDE_OSCURO,
        fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=8, leading=14
    )
    header_style = ParagraphStyle(
        'HeaderStyle', parent=styles['Normal'],
        fontSize=8, textColor=colors.white,
        alignment=TA_CENTER, fontName='Helvetica-Bold'
    )
    contenido_style = ParagraphStyle(
        'ContenidoStyle', parent=styles['Normal'],
        fontSize=7, alignment=TA_LEFT, leading=11
    )
    hora_style = ParagraphStyle(
        'HoraStyle', parent=styles['Normal'],
        fontSize=8, alignment=TA_CENTER,
        fontName='Helvetica-Bold', textColor=COLOR_VERDE_OSCURO
    )

    sesiones_por_fecha = defaultdict(list)
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

    for sesion in sesiones:
        fecha_obj = sesion['fecha']
        fecha_str = fecha_obj.strftime('%Y-%m-%d')
        dia_semana = dias_semana[fecha_obj.weekday()]
        fecha_display = f"{dia_semana} {fecha_obj.day} de {meses[fecha_obj.month - 1]} de {fecha_obj.year}"

        hora_inicio = sesion['hora_inicio']
        hora_fin = sesion['hora_fin']
        if hasattr(hora_inicio, 'seconds'):
            hi = f"{hora_inicio.seconds // 3600:02d}:{(hora_inicio.seconds % 3600) // 60:02d}"
            hf = f"{hora_fin.seconds // 3600:02d}:{(hora_fin.seconds % 3600) // 60:02d}"
        else:
            hi = str(hora_inicio)[:5] if hora_inicio else '--:--'
            hf = str(hora_fin)[:5] if hora_fin else '--:--'

        nombre_parts = filter(None, [
            sesion.get('nombre_ponente', ''),
            sesion.get('apellido_paterno', ''),
            sesion.get('apellido_materno', '')
        ])
        ponente = ' '.join(nombre_parts).strip() or 'No asignado'
        institucion = sesion.get('procedencia_institucion_independiente', '')
        institucion_display = f"🏛️ {institucion}" if institucion else "🎓 Independiente"

        foto_ponente = cargar_imagen(sesion.get('fotografia'), 30, 30) if sesion.get('fotografia') else None

        sesiones_por_fecha[fecha_str].append({
            'fecha_display': fecha_display,
            'hora': f"{hi} - {hf}",
            'nombre': sesion['nombre_de_sesion'] or 'Sin nombre',
            'tipo': sesion['tipo'] or 'N/A',
            'ponente': ponente,
            'institucion': institucion_display,
            'escenario': sesion['escenario_nombre'] or 'N/A',
            'foto': foto_ponente
        })

    elementos = [Spacer(1, 0.2 * inch)]
    col_widths = [0.85*inch, 3.2*inch, 0.9*inch, 1.1*inch, 0.65*inch]

    for fecha_str in sorted(sesiones_por_fecha.keys()):
        sesiones_dia = sesiones_por_fecha[fecha_str]

        cabeceras = [
            Paragraph("<b>HORARIO</b>", header_style),
            Paragraph("<b>SESIÓN / PONENTE / INSTITUCIÓN</b>", header_style),
            Paragraph("<b>TIPO</b>", header_style),
            Paragraph("<b>ESCENARIO</b>", header_style),
            Paragraph("<b>FOTO</b>", header_style)
        ]
        filas = [cabeceras]

        for s in sesiones_dia:
            hora_celda = Paragraph(f"<b>{s['hora']}</b>", hora_style)
            contenido = (
                f"<b><font color='{COLOR_VERDE_OSCURO}'>{s['nombre']}</font></b>"
                f"<br/><font color='#666666' size=7>👤 {s['ponente']}</font>"
                f"<br/><font color='{COLOR_VERDE}' size=7>{s['institucion']}</font>"
            )
            sesion_celda = Paragraph(contenido, contenido_style)
            tipo_celda = Paragraph(s['tipo'], contenido_style)
            escenario_celda = Paragraph(s['escenario'], contenido_style)
            foto_celda = s['foto'] if s['foto'] else Paragraph(
                "📷",
                ParagraphStyle('FotoStyle', parent=contenido_style, alignment=TA_CENTER, fontSize=10)
            )
            filas.append([hora_celda, sesion_celda, tipo_celda, escenario_celda, foto_celda])

        tabla = Table(filas, colWidths=col_widths, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_VERDE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('ALIGN', (3, 0), (3, 0), 'LEFT'),
            ('ALIGN', (4, 0), (4, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.3, COLOR_BORDE),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_VERDE_CLARO]),
            ('PADDING', (0, 1), (-1, -1), 6),
            ('VALIGN', (4, 1), (4, -1), 'MIDDLE'),
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),
        ]))

        # ✅ FIX: título + tabla juntos en KeepTogether — evita título huérfano
        bloque_dia = KeepTogether([
            Paragraph(f"■  {sesiones_dia[0]['fecha_display']}", fecha_style),
            Spacer(1, 0.12 * inch),
            tabla,
            Spacer(1, 0.25 * inch)
        ])
        elementos.append(bloque_dia)

    return elementos


@admin_export_bp.route("/eventos/<int:id_evento>/instituciones-logos")
def get_instituciones_logos(id_evento):
    """Obtiene las instituciones con logos para el evento específico"""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    con = config.conectar_db()
    if not con:
        return jsonify({"success": False, "message": "Error de conexión"}), 500
    
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT 
                    s.procedencia_institucion_independiente AS nombre,
                    s.logo AS logo_path
                FROM sesion s
                WHERE s.id_evento = %s 
                    AND s.procedencia_institucion_independiente IS NOT NULL 
                    AND s.logo IS NOT NULL
                    AND s.logo != ''
                ORDER BY s.procedencia_institucion_independiente
            """, (id_evento,))
            
            instituciones = []
            for idx, row in enumerate(cur.fetchall()):
                instituciones.append({
                    "id": idx + 1,
                    "nombre": row['nombre'],
                    "logo_path": row['logo_path']
                })
            
            print(f"📋 Instituciones encontradas: {len(instituciones)}")  # Debug
            for inst in instituciones:
                print(f"   - {inst['nombre']}: {inst['logo_path']}")
            
            return jsonify({
                "success": True,
                "instituciones": instituciones
            })
    except Exception as e:
        print(f"Error obteniendo instituciones: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()




def generar_pdf_con_logos_personalizados(ev, sesiones, logo_izq_path, logo_centro_path, logo_der_path, logos_participantes):
    """Genera el PDF con logos de encabezado personalizados y logos del pie proporcionales."""
    COLOR_VERDE = colors.HexColor('#70AC46')
    COLOR_VERDE_OSCURO = colors.HexColor('#4A7A2E')
    COLOR_VERDE_CLARO = colors.HexColor('#F0F7EC')
    COLOR_BORDE = colors.HexColor('#C8E6C0')

    buffer = BytesIO()

    # ✅ FIX: topMargin más alto para acomodar los logos grandes del encabezado personalizado
    doc = BaseDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.6*inch, leftMargin=0.6*inch,
        topMargin=1.55*inch, bottomMargin=1.2*inch
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')

    def dibujar_encabezado(canvas_obj, doc):
        canvas_obj.saveState()
        ancho_pagina = letter[0]
        alto_pagina = letter[1]
        # Zona de logos: parte superior
        y_logos_top = alto_pagina - 0.5 * inch  # tope superior de los logos

        logo_h = 0.75 * inch  # alto reservado para logos
        y_logo_base = y_logos_top - logo_h  # base donde se dibuja

        # Logo izquierdo
        if logo_izq_path and os.path.exists(logo_izq_path):
            try:
                img = cargar_imagen_proporcional(logo_izq_path, 0.9 * inch, logo_h)
                if img:
                    img.drawOn(canvas_obj, 0.5 * inch, y_logo_base)
            except Exception as e:
                print(f"Error logo izquierdo: {e}")

        # Logo centro
        if logo_centro_path and os.path.exists(logo_centro_path):
            try:
                img = cargar_imagen_proporcional(logo_centro_path, 1.1 * inch, logo_h)
                if img:
                    img.drawOn(canvas_obj, (ancho_pagina / 2) - (img.drawWidth / 2), y_logo_base)
            except Exception as e:
                print(f"Error logo centro: {e}")

        # Logo derecho
        if logo_der_path and os.path.exists(logo_der_path):
            try:
                img = cargar_imagen_proporcional(logo_der_path, 0.9 * inch, logo_h)
                if img:
                    img.drawOn(canvas_obj, ancho_pagina - 0.5 * inch - img.drawWidth, y_logo_base)
            except Exception as e:
                print(f"Error logo derecho: {e}")

        # Título del evento
        y_titulo = y_logo_base - 0.22 * inch
        canvas_obj.setFont('Helvetica-Bold', 12)
        canvas_obj.setFillColor(COLOR_VERDE_OSCURO)
        canvas_obj.drawCentredString(ancho_pagina / 2, y_titulo, ev['nombre'])

        # Fechas
        fecha_inicio = ev['fecha_inicio'].strftime('%d/%m/%Y') if hasattr(ev['fecha_inicio'], 'strftime') else str(ev['fecha_inicio'])
        fecha_fin = ev['fecha_fin'].strftime('%d/%m/%Y') if hasattr(ev['fecha_fin'], 'strftime') else str(ev['fecha_fin'])
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.setFillColorRGB(0.5, 0.5, 0.5)
        canvas_obj.drawCentredString(ancho_pagina / 2, y_titulo - 0.18 * inch, f"{fecha_inicio} al {fecha_fin}")

        # Línea separadora
        y_linea = y_titulo - 0.33 * inch
        canvas_obj.setStrokeColor(COLOR_VERDE_OSCURO)
        canvas_obj.setLineWidth(1.2)
        canvas_obj.line(0.5 * inch, y_linea, ancho_pagina - 0.5 * inch, y_linea)
        canvas_obj.restoreState()

    def dibujar_pie(canvas_obj, doc):
        canvas_obj.saveState()
        ancho_pagina = letter[0]
        y_base = 0.6 * inch

        canvas_obj.setStrokeColor(COLOR_VERDE)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(0.5 * inch, y_base + 0.15 * inch, ancho_pagina - 0.5 * inch, y_base + 0.15 * inch)

        canvas_obj.setFont('Helvetica-Oblique', 7)
        canvas_obj.setFillColor(COLOR_VERDE)
        lema = "CULTURA QUE INSPIRA, CONOCIMIENTO QUE TRANSFORMA"
        canvas_obj.drawCentredString(ancho_pagina / 2, y_base - 0.05 * inch, lema)

        _dibujar_logos_pie(canvas_obj, logos_participantes, ancho_pagina, y_base)

        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.setFillColorRGB(0.6, 0.6, 0.6)
        canvas_obj.drawRightString(ancho_pagina - 0.5 * inch, 0.25 * inch, f"Página {doc.page}")
        canvas_obj.restoreState()

    def dibujar_encabezado_y_pie(canvas_obj, doc):
        dibujar_encabezado(canvas_obj, doc)
        dibujar_pie(canvas_obj, doc)

    doc.addPageTemplates([PageTemplate(id='Todo', frames=[frame], onPage=dibujar_encabezado_y_pie)])

    elementos = _construir_elementos_tabla(sesiones, COLOR_VERDE, COLOR_VERDE_OSCURO, COLOR_VERDE_CLARO, COLOR_BORDE)
    doc.build(elementos)
    return buffer.getvalue()




@admin_export_bp.route("/eventos/exportar-pdf-alumno")
def alumno_exportar_agenda_pdf():
    """Alumno descarga su agenda personal usando la configuración de logos del evento"""
    if not session.get('user_tipo') == 'alumno':
        return redirect(url_for('auth.login'))
    
    id_alumno = session.get('user_id')
    nombre_alumno = session.get('user_nombre')
    email_alumno = session.get('user_email')
    
    con = config.conectar_db()
    if not con:
        flash("Error de conexión", "error")
        return redirect(url_for("alumno.alumno_agenda"))
    
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM evento WHERE publicado = TRUE AND activo = 1 ORDER BY fecha_publicacion DESC LIMIT 1")
            ev = cur.fetchone()
            if not ev:
                flash("No hay jornada publicada", "warning")
                return redirect(url_for("alumno.alumno_agenda"))
            
            cur.execute("""
                SELECT s.*, ts.nombre_sesion AS tipo, e.nombre_escenario AS escenario_nombre
                FROM inscripciones i
                JOIN sesion s ON i.id_sesion = s.id_sesion
                JOIN tipo_sesion ts ON ts.id_tipo_sesion = s.id_tipo_sesion
                JOIN escenarios e ON e.id_escenario = s.id_escenario
                WHERE i.id_alumno = %s AND s.id_evento = %s
                ORDER BY s.fecha, s.hora_inicio
            """, (id_alumno, ev['id_evento']))
            sesiones = cur.fetchall()
            
            if not sesiones:
                flash("No tienes sesiones inscritas", "warning")
                return redirect(url_for("alumno.alumno_agenda"))
        
        # ========== Cargar configuración de logos guardada ==========
        # Dimensiones para logos del encabezado (alumno)
        logo_header_ancho = 0.65 * inch
        logo_header_alto = 0.55 * inch
        
        # Intentar cargar configuración guardada
        logo_izq, logo_cent, logo_der, logos_participantes = cargar_logos_desde_configuracion(
            ev['id_evento'],
            max_ancho=logo_header_ancho,
            max_alto=logo_header_alto
        )
        
        # Si no hay configuración guardada, usar valores por defecto
        if not logo_izq and not logo_cent and not logo_der:
            print("ℹ️ No hay configuración guardada, usando logos por defecto")
            logo_gobierno = cargar_imagen('static/img/logo_gobierno.png', 55, 50)
            logo_umb = cargar_imagen('static/img/logo_umb.png', 55, 50)
            nombre_limpio = ev['nombre'].replace(' ', '_').replace('ñ', 'n').lower()
            logo_jornada = cargar_imagen(f'static/img/jornadas/{nombre_limpio}.png', 65, 50)
            if not logo_jornada:
                logo_jornada = cargar_imagen('static/img/logo_jornada_default.png', 65, 50)
            
            logo_izq = logo_gobierno
            logo_cent = logo_jornada
            logo_der = logo_umb
        
        # Si no hay logos del pie en la configuración, cargar desde la base de datos
        if not logos_participantes:
            print("ℹ️ No hay logos de pie configurados, cargando desde la base de datos")
            with con.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT s.procedencia_institucion_independiente, s.logo
                    FROM sesion s
                    WHERE s.id_evento = %s AND s.procedencia_institucion_independiente IS NOT NULL AND s.logo IS NOT NULL
                """, (ev['id_evento'],))
                instituciones = cur.fetchall()
            
            for inst in instituciones:
                if inst.get('logo'):
                    logo = cargar_imagen_proporcional(inst['logo'], 0.55 * inch, 0.45 * inch)
                    if logo:
                        logos_participantes.append(logo)
        # ================================================================
        
        pdf_buffer = generar_pdf_para_alumno_con_config(
            ev, sesiones,
            logo_izq, logo_cent, logo_der,
            logos_participantes,
            nombre_alumno, email_alumno
        )
        
        response = make_response(pdf_buffer)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="mi_agenda_{nombre_alumno.replace(" ", "_")}.pdf"'
        return response
        
    except Exception as e:
        print(f"[PDF Alumno Error] {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error al generar tu agenda: {e}", "error")
        return redirect(url_for("alumno.alumno_agenda"))
    finally:
        con.close()

def generar_pdf_para_alumno_con_config(ev, sesiones, logo_izq, logo_cent, logo_der, logos_participantes, nombre_alumno, email_alumno):
    """Genera PDF personalizado para el alumno usando los logos de configuración"""
    COLOR_VERDE = colors.HexColor('#70AC46')
    COLOR_VERDE_OSCURO = colors.HexColor('#4A7A2E')
    COLOR_VERDE_CLARO = colors.HexColor('#F0F7EC')
    COLOR_BORDE = colors.HexColor('#C8E6C0')
    
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.6*inch, leftMargin=0.6*inch,
        topMargin=1.4*inch, bottomMargin=1.2*inch
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    
    def dibujar_encabezado_y_pie(canvas_obj, doc):
        canvas_obj.saveState()
        ancho_pagina = letter[0]
        alto_pagina = letter[1]
        y_logos = alto_pagina - 0.65*inch
        
        # Dibujar logos personalizados del encabezado
        if logo_izq:
            logo_izq.drawOn(canvas_obj, 0.5*inch, y_logos - 0.30*inch)
        if logo_cent:
            logo_cent.drawOn(canvas_obj, (ancho_pagina / 2) - (logo_cent.drawWidth / 2), y_logos - 0.30*inch)
        if logo_der:
            logo_der.drawOn(canvas_obj, ancho_pagina - 0.5*inch - logo_der.drawWidth, y_logos - 0.30*inch)
        
        canvas_obj.setFont('Helvetica-Bold', 11)
        canvas_obj.setFillColor(COLOR_VERDE_OSCURO)
        canvas_obj.drawCentredString(ancho_pagina / 2, y_logos - 0.65*inch, ev['nombre'])
        
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColorRGB(0.5, 0.5, 0.5)
        canvas_obj.drawCentredString(ancho_pagina / 2, y_logos - 0.80*inch, f"Agenda personal de: {nombre_alumno}")
        
        fecha_inicio = ev['fecha_inicio'].strftime('%d/%m/%Y') if hasattr(ev['fecha_inicio'], 'strftime') else str(ev['fecha_inicio'])
        fecha_fin = ev['fecha_fin'].strftime('%d/%m/%Y') if hasattr(ev['fecha_fin'], 'strftime') else str(ev['fecha_fin'])
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.drawCentredString(ancho_pagina / 2, y_logos - 0.93*inch, f"{fecha_inicio} al {fecha_fin}")
        
        y_linea = y_logos - 1.08*inch
        canvas_obj.setStrokeColor(COLOR_VERDE_OSCURO)
        canvas_obj.setLineWidth(1)
        canvas_obj.line(0.5*inch, y_linea, ancho_pagina - 0.5*inch, y_linea)
        canvas_obj.restoreState()
        
        canvas_obj.saveState()
        y_base = 0.65*inch
        
        canvas_obj.setStrokeColor(COLOR_VERDE)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(0.5*inch, y_base + 0.15*inch, ancho_pagina - 0.5*inch, y_base + 0.15*inch)
        
        canvas_obj.setFont('Helvetica-Oblique', 7)
        canvas_obj.setFillColor(COLOR_VERDE)
        lema = "CULTURA QUE INSPIRA, CONOCIMIENTO QUE TRANSFORMA"
        canvas_obj.drawCentredString(ancho_pagina / 2, y_base - 0.05*inch, lema)
        
        _dibujar_logos_pie(canvas_obj, logos_participantes, ancho_pagina, y_base)
        
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.setFillColorRGB(0.6, 0.6, 0.6)
        canvas_obj.drawRightString(ancho_pagina - 0.5*inch, 0.25*inch, f"Página {doc.page}")
        canvas_obj.restoreState()
    
    doc.addPageTemplates([PageTemplate(id='Todo', frames=[frame], onPage=dibujar_encabezado_y_pie)])
    
    elementos = _construir_elementos_tabla(sesiones, COLOR_VERDE, COLOR_VERDE_OSCURO, COLOR_VERDE_CLARO, COLOR_BORDE)
    doc.build(elementos)
    return buffer.getvalue()