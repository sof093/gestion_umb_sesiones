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

def cargar_imagen(ruta, ancho=50, alto=50):
    if not ruta:
        return None
    try:
        # Limpiar la ruta
        ruta_limpia = ruta.replace('\\', '/')
        
        # Posibles rutas a intentar
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

@admin_export_bp.route("/eventos/<int:id_evento>/exportar-pdf")
def exportar_itinerario_pdf(id_evento):
    if not session.get("admin_logged"):
        return redirect(url_for("auth.login"))
    
    con = config.conectar_db()
    if not con:
        flash("Error de conexión", "error")
        return redirect(url_for("admin.admin_sesiones"))
    
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM evento WHERE id_evento = %s", (id_evento,))
            ev = cur.fetchone()
            if not ev:
                flash("Evento no encontrado", "error")
                return redirect(url_for("admin.admin_sesiones"))
            
            cur.execute("""
                SELECT s.*, ts.nombre_sesion AS tipo, e.nombre_escenario AS escenario_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON ts.id_tipo_sesion = s.id_tipo_sesion
                JOIN escenarios e ON e.id_escenario = s.id_escenario
                WHERE s.id_evento = %s
                ORDER BY s.fecha, s.hora_inicio
            """, (id_evento,))
            sesiones = cur.fetchall()
            
            cur.execute("""
                SELECT DISTINCT s.procedencia_institucion_independiente, s.logo
                FROM sesion s
                WHERE s.id_evento = %s AND s.procedencia_institucion_independiente IS NOT NULL AND s.logo IS NOT NULL
            """, (id_evento,))
            instituciones = cur.fetchall()
        
        # Cargar logos
        logo_gobierno = cargar_imagen('static/img/logo_gobierno.png', 55, 50)
        logo_umb = cargar_imagen('static/img/logo_umb.png', 55, 50)
        nombre_limpio = ev['nombre'].replace(' ', '_').replace('ñ', 'n').lower()
        logo_jornada = cargar_imagen(f'static/img/jornadas/{nombre_limpio}.png', 65, 50)
        if not logo_jornada:
            logo_jornada = cargar_imagen('static/img/logo_jornada_default.png', 65, 50)
        
        # ✅ CÓDIGO CORRECTO - Logos del pie desde la BD
        logos_participantes = []
        for inst in instituciones:
            if inst.get('logo'):
                logo = cargar_imagen(inst['logo'], 40, 35)
                if logo:
                    logos_participantes.append(logo)
        
        COLOR_VERDE = colors.HexColor('#70AC46')
        COLOR_VERDE_OSCURO = colors.HexColor('#4A7A2E')
        COLOR_VERDE_CLARO = colors.HexColor('#F0F7EC')
        COLOR_BORDE = colors.HexColor('#C8E6C0')
        
        # Resto del código igual...
        buffer = BytesIO()
        doc = BaseDocTemplate(buffer, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=1.2*inch, bottomMargin=1.1*inch)
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
        
        def dibujar_encabezado_y_pie(canvas, doc):
            # Header
            canvas.saveState()
            ancho_pagina = letter[0]
            alto_pagina = letter[1]
            y_logos = alto_pagina - 0.65*inch
            
            if logo_gobierno:
                logo_gobierno.drawOn(canvas, 0.5*inch, y_logos - 0.30*inch)
            if logo_jornada:
                logo_jornada.drawOn(canvas, (ancho_pagina / 2) - 0.35*inch, y_logos - 0.30*inch)
            if logo_umb:
                logo_umb.drawOn(canvas, ancho_pagina - 0.85*inch, y_logos - 0.30*inch)
            
            canvas.setFont('Helvetica-Bold', 11)
            canvas.setFillColor(COLOR_VERDE_OSCURO)
            canvas.drawCentredString(ancho_pagina / 2, y_logos - 0.65*inch, ev['nombre'])
            
            fecha_inicio = ev['fecha_inicio'].strftime('%d/%m/%Y') if hasattr(ev['fecha_inicio'], 'strftime') else str(ev['fecha_inicio'])
            fecha_fin = ev['fecha_fin'].strftime('%d/%m/%Y') if hasattr(ev['fecha_fin'], 'strftime') else str(ev['fecha_fin'])
            canvas.setFont('Helvetica', 8)
            canvas.setFillColorRGB(0.5, 0.5, 0.5)
            canvas.drawCentredString(ancho_pagina / 2, y_logos - 0.80*inch, f"{fecha_inicio} al {fecha_fin}")
            
            y_linea = y_logos - 0.95*inch
            canvas.setStrokeColor(COLOR_VERDE_OSCURO)
            canvas.setLineWidth(1)
            canvas.line(0.5*inch, y_linea, ancho_pagina - 0.5*inch, y_linea)
            canvas.restoreState()
            
            # Footer
            canvas.saveState()
            y_base = 0.65*inch
            
            canvas.setStrokeColor(COLOR_VERDE)
            canvas.setLineWidth(0.5)
            canvas.line(0.5*inch, y_base + 0.15*inch, ancho_pagina - 0.5*inch, y_base + 0.15*inch)
            
            canvas.setFont('Helvetica-Oblique', 7)
            canvas.setFillColor(COLOR_VERDE)
            lema = "CULTURA QUE INSPIRA, CONOCIMIENTO QUE TRANSFORMA"
            canvas.drawCentredString(ancho_pagina / 2, y_base - 0.05*inch, lema)
            
            if logos_participantes:
                logos_mostrar = logos_participantes[:6]
                ancho_logo = 0.45 * inch
                alto_logo = 0.35 * inch
                espacio = 0.10 * inch
                total_ancho = len(logos_mostrar) * ancho_logo + (len(logos_mostrar) - 1) * espacio
                inicio_x = (ancho_pagina - total_ancho) / 2
                y_logos = y_base - 0.55 * inch
                
                for i, logo_img in enumerate(logos_mostrar):
                    x = inicio_x + i * (ancho_logo + espacio)
                    logo_img.drawWidth = ancho_logo
                    logo_img.drawHeight = alto_logo
                    logo_img.drawOn(canvas, x, y_logos)
            
            canvas.setFont('Helvetica', 6)
            canvas.setFillColorRGB(0.6, 0.6, 0.6)
            canvas.drawRightString(ancho_pagina - 0.5*inch, 0.25*inch, f"Página {doc.page}")
            canvas.restoreState()
        
        doc.addPageTemplates([PageTemplate(id='Todo', frames=[frame], onPage=dibujar_encabezado_y_pie)])
        
        # Construir contenido de la tabla (igual que antes)
        styles = getSampleStyleSheet()
        fecha_style = ParagraphStyle('FechaStyle', parent=styles['Heading3'], fontSize=12, textColor=COLOR_VERDE_OSCURO, fontName='Helvetica-Bold', spaceAfter=12, spaceBefore=8, leading=14)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=8, textColor=colors.white, alignment=TA_CENTER, fontName='Helvetica-Bold')
        contenido_style = ParagraphStyle('ContenidoStyle', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT, leading=11)
        hora_style = ParagraphStyle('HoraStyle', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=COLOR_VERDE_OSCURO)
        
        sesiones_por_fecha = defaultdict(list)
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
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
            
            nombre_parts = filter(None, [sesion.get('nombre_ponente', ''), sesion.get('apellido_paterno', ''), sesion.get('apellido_materno', '')])
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
        
        elementos = [Spacer(1, 0.35*inch)]
        col_widths = [0.85*inch, 3.2*inch, 0.9*inch, 1.1*inch, 0.65*inch]
        
        for fecha_str in sorted(sesiones_por_fecha.keys()):
            sesiones_dia = sesiones_por_fecha[fecha_str]
            cabeceras = [Paragraph("<b>HORARIO</b>", header_style), Paragraph("<b>SESIÓN / PONENTE / INSTITUCIÓN</b>", header_style), Paragraph("<b>TIPO</b>", header_style), Paragraph("<b>ESCENARIO</b>", header_style), Paragraph("<b>FOTO</b>", header_style)]
            filas = [cabeceras]
            
            for s in sesiones_dia:
                hora_celda = Paragraph(f"<b>{s['hora']}</b>", hora_style)
                contenido = f"<b><font color='{COLOR_VERDE_OSCURO}'>{s['nombre']}</font></b><br/><font color='#666666' size=7>👤 {s['ponente']}</font><br/><font color='{COLOR_VERDE}' size=7>{s['institucion']}</font>"
                sesion_celda = Paragraph(contenido, contenido_style)
                tipo_celda = Paragraph(s['tipo'], contenido_style)
                escenario_celda = Paragraph(s['escenario'], contenido_style)
                foto_celda = s['foto'] if s['foto'] else Paragraph("📷", ParagraphStyle('FotoStyle', parent=contenido_style, alignment=TA_CENTER, fontSize=10))
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
            
            # Fecha como elemento independiente (arriba)
            elementos.append(Paragraph(f"■  {sesiones_dia[0]['fecha_display']}", fecha_style))
            # Espacio entre fecha y tabla
            elementos.append(Spacer(1, 0.15*inch))
            # Tabla con sus espacios
            elementos.append(KeepTogether([tabla, Spacer(1, 0.25*inch)]))

        doc.build(elementos)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="itinerario_{ev["nombre"].replace(" ", "_")}.pdf"'
        buffer.close()
        return response
        
    except Exception as e:
        print(f"[PDF Error] {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error al generar PDF: {e}", "error")
        return redirect(url_for("admin.admin_sesiones"))
    finally:
        con.close()

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
            
            return jsonify({
                "success": True,
                "instituciones": instituciones
            })
    except Exception as e:
        print(f"Error obteniendo instituciones: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()

@admin_export_bp.route("/eventos/exportar-pdf-personalizado", methods=['POST'])
def exportar_pdf_personalizado():
    """Genera PDF con logos personalizados subidos por el admin"""
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    evento_id = request.form.get('evento_id')
    logos_pie_json = request.form.get('logos_pie', '[]')
    
    if not evento_id:
        return jsonify({"success": False, "message": "ID de evento requerido"}), 400
    
    try:
        logos_pie = json.loads(logos_pie_json)
    except:
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
        
        # Procesar logos subidos temporalmente
        temp_dir = os.path.join('static', 'temp_logos')
        os.makedirs(temp_dir, exist_ok=True)
        
        logo_paths = {
            'izquierda': None,
            'centro': None,
            'derecha': None
        }
        
        # Guardar logos subidos temporalmente
        for position in ['izquierda', 'centro', 'derecha']:
            if f'logo_{position}' in request.files:
                file = request.files[f'logo_{position}']
                if file and file.filename:
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"temp_{position}_{evento_id}_{int(time.time())}.{ext}"
                    filepath = os.path.join(temp_dir, filename)
                    file.save(filepath)
                    logo_paths[position] = filepath
                    print(f"✅ Logo {position} guardado en: {filepath}")
        
        # Obtener logos del pie seleccionados
        logos_participantes = []
        print(f"🔍 Procesando {len(logos_pie)} logos seleccionados para el pie")
        
        for logo_path in logos_pie:
            print(f"  Buscando logo: {logo_path}")
            # Buscar el logo en diferentes rutas
            full_path = None
            if os.path.exists(logo_path):
                full_path = logo_path
            elif os.path.exists(os.path.join('static', logo_path.lstrip('/'))):
                full_path = os.path.join('static', logo_path.lstrip('/'))
            elif os.path.exists(os.path.join('static/uploads/sesiones', os.path.basename(logo_path))):
                full_path = os.path.join('static/uploads/sesiones', os.path.basename(logo_path))
            
            if full_path and os.path.exists(full_path):
                img = cargar_imagen(full_path, 55, 45)
                if img:
                    logos_participantes.append(img)
                    print(f"    ✅ Logo cargado: {full_path}")
                else:
                    print(f"    ❌ No se pudo crear Image object")
            else:
                print(f"    ❌ Archivo no existe: {logo_path}")
        
        print(f"📊 Total logos en pie: {len(logos_participantes)}")
        
        # Generar PDF con logos personalizados
        pdf_buffer = generar_pdf_con_logos_personalizados(
            ev, sesiones, 
            logo_paths['izquierda'],
            logo_paths['centro'],
            logo_paths['derecha'],
            logos_participantes
        )
        
        # Limpiar archivos temporales
        for path in logo_paths.values():
            if path and os.path.exists(path):
                os.remove(path)
                print(f"🗑️ Eliminado temporal: {path}")
        
        response = make_response(pdf_buffer)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="itinerario_{ev["nombre"].replace(" ", "_")}_personalizado.pdf"'
        return response
        
    except Exception as e:
        print(f"Error generando PDF personalizado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()

def generar_pdf_con_logos_personalizados(ev, sesiones, logo_izq_path, logo_centro_path, logo_der_path, logos_participantes):
    """Función auxiliar que genera el PDF con logos personalizados"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image, Paragraph, PageTemplate, Frame, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from io import BytesIO
    
    COLOR_VERDE = colors.HexColor('#70AC46')
    COLOR_VERDE_OSCURO = colors.HexColor('#4A7A2E')
    COLOR_VERDE_CLARO = colors.HexColor('#F0F7EC')
    COLOR_BORDE = colors.HexColor('#C8E6C0')
    
    buffer = BytesIO()
    
    def header(canvas, doc):
        canvas.saveState()
        ancho_pagina = letter[0]
        alto_pagina = letter[1]
        y_logos = alto_pagina - 0.75*inch
        
        # Logos personalizados con tamaños mejorados
        if logo_izq_path and os.path.exists(logo_izq_path):
            try:
                logo_izq = Image(logo_izq_path, width=0.9*inch, height=0.7*inch)
                logo_izq.drawOn(canvas, 0.5*inch, y_logos - 0.25*inch)
                print(f"✅ Logo izquierdo dibujado")
            except Exception as e:
                print(f"Error cargando logo izquierdo: {e}")
        
        if logo_centro_path and os.path.exists(logo_centro_path):
            try:
                logo_centro = Image(logo_centro_path, width=1.1*inch, height=0.8*inch)
                logo_centro.drawOn(canvas, (ancho_pagina / 2) - 0.55*inch, y_logos - 0.25*inch)
                print(f"✅ Logo centro dibujado")
            except Exception as e:
                print(f"Error cargando logo centro: {e}")
        
        if logo_der_path and os.path.exists(logo_der_path):
            try:
                logo_der = Image(logo_der_path, width=0.9*inch, height=0.7*inch)
                logo_der.drawOn(canvas, ancho_pagina - 1.4*inch, y_logos - 0.25*inch)
                print(f"✅ Logo derecho dibujado")
            except Exception as e:
                print(f"Error cargando logo derecho: {e}")
        
        # Título del evento
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(COLOR_VERDE_OSCURO)
        canvas.drawCentredString(ancho_pagina / 2, y_logos - 0.85*inch, ev['nombre'])
        
        # Fechas
        fecha_inicio = ev['fecha_inicio'].strftime('%d/%m/%Y') if hasattr(ev['fecha_inicio'], 'strftime') else str(ev['fecha_inicio'])
        fecha_fin = ev['fecha_fin'].strftime('%d/%m/%Y') if hasattr(ev['fecha_fin'], 'strftime') else str(ev['fecha_fin'])
        canvas.setFont('Helvetica', 9)
        canvas.setFillColorRGB(0.5, 0.5, 0.5)
        canvas.drawCentredString(ancho_pagina / 2, y_logos - 1.05*inch, f"{fecha_inicio} al {fecha_fin}")
        
        # Línea separadora
        y_linea = y_logos - 1.2*inch
        canvas.setStrokeColor(COLOR_VERDE_OSCURO)
        canvas.setLineWidth(1.2)
        canvas.line(0.5*inch, y_linea, ancho_pagina - 0.5*inch, y_linea)
        canvas.restoreState()
    
    def footer(canvas, doc):
        canvas.saveState()
        ancho_pagina = letter[0]
        y_base = 0.6*inch
        
        # Línea decorativa
        canvas.setStrokeColor(COLOR_VERDE)
        canvas.setLineWidth(0.5)
        canvas.line(0.5*inch, y_base + 0.15*inch, ancho_pagina - 0.5*inch, y_base + 0.15*inch)
        
        # Lema
        canvas.setFont('Helvetica-Oblique', 7)
        canvas.setFillColor(COLOR_VERDE)
        lema = "CULTURA QUE INSPIRA, CONOCIMIENTO QUE TRANSFORMA"
        canvas.drawCentredString(ancho_pagina / 2, y_base - 0.05*inch, lema)
        
        # Logos de instituciones
        if logos_participantes and len(logos_participantes) > 0:
            print(f"🎨 Dibujando {len(logos_participantes)} logos en el pie")
            
            ancho_logo = 0.55 * inch
            alto_logo = 0.45 * inch
            espacio = 0.12 * inch
            logos_por_fila = 6
            
            num_filas = (len(logos_participantes) + logos_por_fila - 1) // logos_por_fila
            y_inicial = y_base - 0.65 * inch
            alto_fila = alto_logo + 0.1 * inch
            
            for fila in range(num_filas):
                inicio = fila * logos_por_fila
                fin = min(inicio + logos_por_fila, len(logos_participantes))
                logos_fila = logos_participantes[inicio:fin]
                
                total_ancho = len(logos_fila) * ancho_logo + (len(logos_fila) - 1) * espacio
                inicio_x = (ancho_pagina - total_ancho) / 2
                
                for i, logo_img in enumerate(logos_fila):
                    x = inicio_x + i * (ancho_logo + espacio)
                    y_logo = y_inicial - (fila * alto_fila)
                    logo_img.drawWidth = ancho_logo
                    logo_img.drawHeight = alto_logo
                    logo_img.drawOn(canvas, x, y_logo)
                    print(f"  Logo {i+1} dibujado")
        else:
            print("⚠️ No hay logos para mostrar en el pie")
        
        # Número de página
        canvas.setFont('Helvetica', 6)
        canvas.setFillColorRGB(0.6, 0.6, 0.6)
        canvas.drawRightString(ancho_pagina - 0.5*inch, 0.25*inch, f"Página {doc.page}")
        canvas.restoreState()
    
    # Configurar documento
    doc = BaseDocTemplate(buffer, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=1.2*inch, bottomMargin=1.1*inch)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    
    def dibujar_encabezado_y_pie(canvas, doc):
        header(canvas, doc)
        footer(canvas, doc)
    
    doc.addPageTemplates([PageTemplate(id='Todo', frames=[frame], onPage=dibujar_encabezado_y_pie)])
    
    # Crear contenido de la tabla
    elementos = [Spacer(1, 0.35*inch)]
    styles = getSampleStyleSheet()
    fecha_style = ParagraphStyle('FechaStyle', parent=styles['Heading3'], fontSize=11, textColor=COLOR_VERDE_OSCURO, fontName='Helvetica-Bold', spaceAfter=8, spaceBefore=8)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=8, textColor=colors.white, alignment=TA_CENTER, fontName='Helvetica-Bold')
    contenido_style = ParagraphStyle('ContenidoStyle', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT, leading=11)
    hora_style = ParagraphStyle('HoraStyle', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=COLOR_VERDE_OSCURO)
    
    sesiones_por_fecha = defaultdict(list)
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
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
        
        nombre_parts = filter(None, [sesion.get('nombre_ponente', ''), sesion.get('apellido_paterno', ''), sesion.get('apellido_materno', '')])
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
    
    col_widths = [0.85*inch, 3.2*inch, 0.9*inch, 1.1*inch, 0.65*inch]
    
    for fecha_str in sorted(sesiones_por_fecha.keys()):
        sesiones_dia = sesiones_por_fecha[fecha_str]
        cabeceras = [Paragraph("<b>HORARIO</b>", header_style), Paragraph("<b>SESIÓN / PONENTE / INSTITUCIÓN</b>", header_style), Paragraph("<b>TIPO</b>", header_style), Paragraph("<b>ESCENARIO</b>", header_style), Paragraph("<b>FOTO</b>", header_style)]
        filas = [cabeceras]
        
        for s in sesiones_dia:
            hora_celda = Paragraph(f"<b>{s['hora']}</b>", hora_style)
            contenido = f"<b><font color='{COLOR_VERDE_OSCURO}'>{s['nombre']}</font></b><br/><font color='#666666' size=7>👤 {s['ponente']}</font><br/><font color='{COLOR_VERDE}' size=7>{s['institucion']}</font>"
            sesion_celda = Paragraph(contenido, contenido_style)
            tipo_celda = Paragraph(s['tipo'], contenido_style)
            escenario_celda = Paragraph(s['escenario'], contenido_style)
            foto_celda = s['foto'] if s['foto'] else Paragraph("📷", ParagraphStyle('FotoStyle', parent=contenido_style, alignment=TA_CENTER, fontSize=10))
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
        
        
        # Fecha como elemento independiente (arriba)
        elementos.append(Paragraph(f"■  {sesiones_dia[0]['fecha_display']}", fecha_style))
        # Espacio entre fecha y tabla
        elementos.append(Spacer(1, 0.15*inch))
        # Tabla con sus espacios
        elementos.append(KeepTogether([tabla, Spacer(1, 0.25*inch)]))

    doc.build(elementos)
    return buffer.getvalue()

@admin_export_bp.route("/eventos/exportar-pdf-alumno")
def alumno_exportar_agenda_pdf():
    """Alumno descarga su agenda personal con los logos configurados por el admin"""
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
            # Obtener el evento activo
            cur.execute("SELECT * FROM evento WHERE publicado = TRUE AND activo = 1 ORDER BY fecha_publicacion DESC LIMIT 1")
            ev = cur.fetchone()
            if not ev:
                flash("No hay jornada publicada", "warning")
                return redirect(url_for("alumno.alumno_agenda"))
            
            # Obtener SOLO las sesiones del alumno
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
            
            # Obtener logos configurados por el admin (misma lógica que el PDF de admin)
            cur.execute("""
                SELECT DISTINCT s.procedencia_institucion_independiente, s.logo
                FROM sesion s
                WHERE s.id_evento = %s AND s.procedencia_institucion_independiente IS NOT NULL AND s.logo IS NOT NULL
            """, (ev['id_evento'],))
            instituciones = cur.fetchall()
        
        # Cargar logos (igual que en exportar_itinerario_pdf)
        logo_gobierno = cargar_imagen('static/img/logo_gobierno.png', 55, 50)
        logo_umb = cargar_imagen('static/img/logo_umb.png', 55, 50)
        nombre_limpio = ev['nombre'].replace(' ', '_').replace('ñ', 'n').lower()
        logo_jornada = cargar_imagen(f'static/img/jornadas/{nombre_limpio}.png', 65, 50)
        if not logo_jornada:
            logo_jornada = cargar_imagen('static/img/logo_jornada_default.png', 65, 50)
        
        # Logos del pie desde la BD
        logos_participantes = []
        for inst in instituciones:
            if inst.get('logo'):
                logo = cargar_imagen(inst['logo'], 40, 35)
                if logo:
                    logos_participantes.append(logo)
        
        # Generar PDF específico para alumno
        pdf_buffer = generar_pdf_para_alumno(
            ev, sesiones, 
            logo_gobierno, logo_jornada, logo_umb,
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


def generar_pdf_para_alumno(ev, sesiones, logo_gobierno, logo_jornada, logo_umb, logos_participantes, nombre_alumno, email_alumno):
    """Genera PDF personalizado para el alumno con SOLO sus sesiones inscritas"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image, Paragraph, PageTemplate, Frame, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from io import BytesIO
    
    COLOR_VERDE = colors.HexColor('#70AC46')
    COLOR_VERDE_OSCURO = colors.HexColor('#4A7A2E')
    COLOR_VERDE_CLARO = colors.HexColor('#F0F7EC')
    COLOR_BORDE = colors.HexColor('#C8E6C0')
    
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter, rightMargin=0.6*inch, leftMargin=0.6*inch, topMargin=1.2*inch, bottomMargin=1.1*inch)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    
    def dibujar_encabezado_y_pie(canvas, doc):
        # Header (igual que el PDF de admin)
        canvas.saveState()
        ancho_pagina = letter[0]
        alto_pagina = letter[1]
        y_logos = alto_pagina - 0.65*inch
        
        if logo_gobierno:
            logo_gobierno.drawOn(canvas, 0.5*inch, y_logos - 0.30*inch)
        if logo_jornada:
            logo_jornada.drawOn(canvas, (ancho_pagina / 2) - 0.35*inch, y_logos - 0.30*inch)
        if logo_umb:
            logo_umb.drawOn(canvas, ancho_pagina - 0.85*inch, y_logos - 0.30*inch)
        
        canvas.setFont('Helvetica-Bold', 11)
        canvas.setFillColor(COLOR_VERDE_OSCURO)
        canvas.drawCentredString(ancho_pagina / 2, y_logos - 0.65*inch, ev['nombre'])
        
        # Subtítulo personalizado para el alumno
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorRGB(0.5, 0.5, 0.5)
        canvas.drawCentredString(ancho_pagina / 2, y_logos - 0.80*inch, f"Agenda personal de: {nombre_alumno}")
        
        fecha_inicio = ev['fecha_inicio'].strftime('%d/%m/%Y') if hasattr(ev['fecha_inicio'], 'strftime') else str(ev['fecha_inicio'])
        fecha_fin = ev['fecha_fin'].strftime('%d/%m/%Y') if hasattr(ev['fecha_fin'], 'strftime') else str(ev['fecha_fin'])
        canvas.setFont('Helvetica', 7)
        canvas.drawCentredString(ancho_pagina / 2, y_logos - 0.93*inch, f"{fecha_inicio} al {fecha_fin}")
        
        y_linea = y_logos - 1.05*inch
        canvas.setStrokeColor(COLOR_VERDE_OSCURO)
        canvas.setLineWidth(1)
        canvas.line(0.5*inch, y_linea, ancho_pagina - 0.5*inch, y_linea)
        canvas.restoreState()
        
        # Footer (igual que el PDF de admin)
        canvas.saveState()
        y_base = 0.65*inch
        
        canvas.setStrokeColor(COLOR_VERDE)
        canvas.setLineWidth(0.5)
        canvas.line(0.5*inch, y_base + 0.15*inch, ancho_pagina - 0.5*inch, y_base + 0.15*inch)
        
        canvas.setFont('Helvetica-Oblique', 7)
        canvas.setFillColor(COLOR_VERDE)
        lema = "CULTURA QUE INSPIRA, CONOCIMIENTO QUE TRANSFORMA"
        canvas.drawCentredString(ancho_pagina / 2, y_base - 0.05*inch, lema)
        
        if logos_participantes:
            logos_mostrar = logos_participantes[:6]
            ancho_logo = 0.45 * inch
            alto_logo = 0.35 * inch
            espacio = 0.10 * inch
            total_ancho = len(logos_mostrar) * ancho_logo + (len(logos_mostrar) - 1) * espacio
            inicio_x = (ancho_pagina - total_ancho) / 2
            y_logos = y_base - 0.55 * inch
            
            for i, logo_img in enumerate(logos_mostrar):
                x = inicio_x + i * (ancho_logo + espacio)
                logo_img.drawWidth = ancho_logo
                logo_img.drawHeight = alto_logo
                logo_img.drawOn(canvas, x, y_logos)
        
        canvas.setFont('Helvetica', 6)
        canvas.setFillColorRGB(0.6, 0.6, 0.6)
        canvas.drawRightString(ancho_pagina - 0.5*inch, 0.25*inch, f"Página {doc.page}")
        canvas.restoreState()
    
    doc.addPageTemplates([PageTemplate(id='Todo', frames=[frame], onPage=dibujar_encabezado_y_pie)])
    
    # Construir contenido (mismo estilo que el PDF de admin)
    styles = getSampleStyleSheet()
    fecha_style = ParagraphStyle('FechaStyle', parent=styles['Heading3'], fontSize=12, textColor=COLOR_VERDE_OSCURO, fontName='Helvetica-Bold', spaceAfter=12, spaceBefore=8, leading=14)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=8, textColor=colors.white, alignment=TA_CENTER, fontName='Helvetica-Bold')
    contenido_style = ParagraphStyle('ContenidoStyle', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT, leading=11)
    hora_style = ParagraphStyle('HoraStyle', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=COLOR_VERDE_OSCURO)
    
    sesiones_por_fecha = defaultdict(list)
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
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
        
        nombre_parts = filter(None, [sesion.get('nombre_ponente', ''), sesion.get('apellido_paterno', ''), sesion.get('apellido_materno', '')])
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
    
    elementos = [Spacer(1, 0.35*inch)]
    col_widths = [0.85*inch, 3.2*inch, 0.9*inch, 1.1*inch, 0.65*inch]
    
    for fecha_str in sorted(sesiones_por_fecha.keys()):
        sesiones_dia = sesiones_por_fecha[fecha_str]
        cabeceras = [Paragraph("<b>HORARIO</b>", header_style), Paragraph("<b>SESIÓN / PONENTE / INSTITUCIÓN</b>", header_style), Paragraph("<b>TIPO</b>", header_style), Paragraph("<b>ESCENARIO</b>", header_style), Paragraph("<b>FOTO</b>", header_style)]
        filas = [cabeceras]
        
        for s in sesiones_dia:
            hora_celda = Paragraph(f"<b>{s['hora']}</b>", hora_style)
            contenido = f"<b><font color='{COLOR_VERDE_OSCURO}'>{s['nombre']}</font></b><br/><font color='#666666' size=7>👤 {s['ponente']}</font><br/><font color='{COLOR_VERDE}' size=7>{s['institucion']}</font>"
            sesion_celda = Paragraph(contenido, contenido_style)
            tipo_celda = Paragraph(s['tipo'], contenido_style)
            escenario_celda = Paragraph(s['escenario'], contenido_style)
            foto_celda = s['foto'] if s['foto'] else Paragraph("📷", ParagraphStyle('FotoStyle', parent=contenido_style, alignment=TA_CENTER, fontSize=10))
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
        
        elementos.append(Paragraph(f"■  {sesiones_dia[0]['fecha_display']}", fecha_style))
        elementos.append(Spacer(1, 0.15*inch))
        elementos.append(KeepTogether([tabla, Spacer(1, 0.25*inch)]))
    
    doc.build(elementos)
    return buffer.getvalue()