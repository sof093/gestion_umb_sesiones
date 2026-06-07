from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from datetime import datetime, timedelta
import config

admin_eventos_bp = Blueprint('admin_eventos', __name__, url_prefix='/admin')

def _dias_evento(fecha_inicio, fecha_fin):
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    
    dias = []
    current = fecha_inicio
    while current <= fecha_fin:
        if current.weekday() < 5:
            dias.append(current)
        current += timedelta(days=1)
    return dias

# ==================== API DE EVENTOS ====================
@admin_eventos_bp.route("/api/eventos", methods=["GET"])
def api_listar_eventos():
    if not session.get("admin_logged"):
        return jsonify({"error": "No autorizado"}), 401
    
    con = config.conectar_db()
    if not con:
        return jsonify([]), 500
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT e.*, COUNT(s.id_sesion) AS total_sesiones
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
                    d[campo] = d[campo].strftime("%Y-%m-%d" if "fecha" in campo else "%Y-%m-%d %H:%M:%S")
            result.append(d)
        return jsonify(result)
    except Exception as e:
        print(f"[api_listar_eventos] {e}")
        return jsonify([]), 500
    finally:
        con.close()

@admin_eventos_bp.route("/api/eventos", methods=["POST"])
def api_crear_evento():
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.get_json()
    nombre = (data.get("nombre") or "").strip()
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    descripcion = (data.get("descripcion") or "").strip() or None
    activar = bool(data.get("activar", False))
    
    if not nombre or not fecha_inicio or not fecha_fin:
        return jsonify({"success": False, "message": "Faltan campos requeridos"})
    
    try:
        fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Formato de fecha inválido"})
    
    if ff < fi:
        return jsonify({"success": False, "message": "La fecha fin no puede ser anterior a la fecha inicio"})
    
    dias_habiles = _dias_evento(fi, ff)
    if not dias_habiles:
        return jsonify({"success": False, "message": "El rango no contiene días hábiles"})
    
    anio = fi.year
    con = config.conectar_db()
    
    try:
        with con.cursor() as cur:
            if activar:
                cur.execute("UPDATE evento SET activo = 0")
            cur.execute("INSERT INTO evento (nombre, anio, fecha_inicio, fecha_fin, descripcion, activo) VALUES (%s, %s, %s, %s, %s, %s)",
                       (nombre, anio, fi, ff, descripcion, 1 if activar else 0))
            nuevo_id = cur.lastrowid
        con.commit()
        return jsonify({"success": True, "message": "Evento creado", "id_evento": nuevo_id, "dias_habiles": len(dias_habiles)})
    except Exception as e:
        con.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()

@admin_eventos_bp.route("/api/eventos/<int:id_evento>", methods=["PUT"])
def api_editar_evento(id_evento):
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    data = request.get_json()
    nombre = (data.get("nombre") or "").strip()
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    descripcion = (data.get("descripcion") or "").strip() or None
    
    if not nombre or not fecha_inicio or not fecha_fin:
        return jsonify({"success": False, "message": "Faltan campos"})
    
    try:
        fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "message": "Fecha inválida"})
    
    con = config.conectar_db()
    try:
        with con.cursor() as cur:
            cur.execute("UPDATE evento SET nombre=%s, anio=%s, fecha_inicio=%s, fecha_fin=%s, descripcion=%s WHERE id_evento=%s",
                       (nombre, fi.year, fi, ff, descripcion, id_evento))
        con.commit()
        return jsonify({"success": True, "message": "Evento actualizado"})
    except Exception as e:
        con.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        con.close()

@admin_eventos_bp.route("/api/eventos/<int:id_evento>/activar", methods=["POST"])
def api_activar_evento(id_evento):
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    con = config.conectar_db()
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

@admin_eventos_bp.route("/api/eventos/<int:id_evento>", methods=["DELETE"])
def api_eliminar_evento(id_evento):
    if not session.get("admin_logged"):
        return jsonify({"success": False, "message": "No autorizado"}), 401
    
    con = config.conectar_db()
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

@admin_eventos_bp.route("/api/eventos/<int:id_evento>/publicar", methods=['POST'])
def api_publicar_evento(id_evento):
    if not session.get('admin_logged'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    data = request.get_json()
    publicado = data.get('publicado', False)
    con = config.conectar_db()
    
    try:
        with con.cursor() as cur:
            if publicado:
                cur.execute("UPDATE evento SET publicado = FALSE, activo = 0")
                cur.execute("UPDATE evento SET publicado = TRUE, activo = 1, fecha_publicacion = %s WHERE id_evento = %s", (datetime.now(), id_evento))
            else:
                cur.execute("UPDATE evento SET publicado = FALSE, fecha_publicacion = NULL WHERE id_evento = %s", (id_evento,))
        con.commit()
        return jsonify({'success': True, 'message': 'Jornada publicada' if publicado else 'Jornada ocultada'})
    except Exception as e:
        con.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        con.close()


# ==================== API: SESIONES DE UN EVENTO ====================
@admin_eventos_bp.route("/api/eventos/<int:id_evento>/sesiones")
def api_evento_sesiones(id_evento):
    if not session.get("admin_logged"):
        return jsonify({"error": "No autorizado"}), 401
    
    con = config.conectar_db()
    if not con:
        return jsonify([]), 500
    
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT s.*, ts.nombre_sesion as tipo, e.nombre_escenario as escenario_nombre,
                       c.nombre_carrera as carrera_nombre
                FROM sesion s
                JOIN tipo_sesion ts ON s.id_tipo_sesion = ts.id_tipo_sesion
                JOIN escenarios e ON s.id_escenario = e.id_escenario
                LEFT JOIN carreras c ON s.id_carrera = c.id_carrera
                WHERE s.id_evento = %s
                ORDER BY s.fecha ASC, s.hora_inicio ASC
            """, (id_evento,))
            sesiones = cur.fetchall()
        
        resultado = []
        for sesion in sesiones:
            item = dict(sesion)
            # Convertir fechas
            if item.get('fecha'):
                item['fecha_str'] = item['fecha'].strftime('%Y-%m-%d')
                item['fecha'] = item['fecha'].strftime('%Y-%m-%d')
            
            # Convertir horas
            for campo in ('hora_inicio', 'hora_fin'):
                val = item.get(campo)
                if val:
                    if hasattr(val, 'strftime'):
                        item[campo] = val.strftime('%H:%M')
                        item[f'{campo}_str'] = val.strftime('%H:%M')
                    elif hasattr(val, 'seconds'):
                        horas = val.seconds // 3600
                        minutos = (val.seconds % 3600) // 60
                        item[campo] = f"{horas:02d}:{minutos:02d}"
                        item[f'{campo}_str'] = f"{horas:02d}:{minutos:02d}"
            
            resultado.append(item)
        
        return jsonify(resultado)
    except Exception as e:
        print(f"[api_evento_sesiones] {e}")
        return jsonify([]), 500
    finally:
        con.close()


# ==================== API: CONFLICTOS DE UN EVENTO ====================
@admin_eventos_bp.route("/api/eventos/<int:id_evento>/conflictos")
def api_evento_conflictos(id_evento):
    if not session.get("admin_logged"):
        return jsonify({"error": "No autorizado"}), 401
    
    con = config.conectar_db()
    if not con:
        return jsonify([]), 500
    
    try:
        with con.cursor() as cur:
            # Buscar conflictos: sesiones que comparten mismo escenario, fecha y horario superpuesto
            cur.execute("""
                SELECT 
                    s1.id_sesion as id_sesion_a,
                    s1.nombre_de_sesion as sesion_a,
                    s2.id_sesion as id_sesion_b,
                    s2.nombre_de_sesion as sesion_b,
                    e.nombre_escenario,
                    s1.fecha
                FROM sesion s1
                JOIN sesion s2 ON s1.id_escenario = s2.id_escenario 
                              AND s1.fecha = s2.fecha 
                              AND s1.id_sesion < s2.id_sesion
                              AND s1.id_evento = %s
                              AND s2.id_evento = %s
                JOIN escenarios e ON e.id_escenario = s1.id_escenario
                WHERE (
                    (s1.hora_inicio < s2.hora_fin AND s1.hora_fin > s2.hora_inicio)
                )
                ORDER BY s1.fecha, e.nombre_escenario
            """, (id_evento, id_evento))
            conflictos = cur.fetchall()
        
        resultado = []
        for c in conflictos:
            item = dict(c)
            if item.get('fecha'):
                item['fecha'] = item['fecha'].strftime('%Y-%m-%d')
            resultado.append(item)
        
        return jsonify(resultado)
    except Exception as e:
        print(f"[api_evento_conflictos] {e}")
        return jsonify([]), 500
    finally:
        con.close()


@admin_eventos_bp.route("/api/eventos/<int:id_evento>/info")
def api_info_evento(id_evento):
    if not session.get("admin_logged"):
        return jsonify({"error": "No autorizado"}), 401
    
    con = config.conectar_db()
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
        d["fecha_inicio"] = fi.strftime("%Y-%m-%d")
        d["fecha_fin"] = ff.strftime("%Y-%m-%d")
        d["dias_habiles"] = [dia.strftime("%Y-%m-%d") for dia in dias]
        d["total_dias"] = len(dias)
        return jsonify(d)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        con.close()

