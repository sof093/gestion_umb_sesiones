// ============================================================
//  calendario.js — UES San José del Rincón
// ============================================================

"use strict";

/* ──────────────────────────────────────────────────────────
   ESTADO GLOBAL
────────────────────────────────────────────────────────── */
const CalState = {
  eventos:         [],
  eventoActivo:    null,
  sesionesEvento:  [],
  conflictos:      [],
  diasHabiles:     [],
  vistaActual:     "calendario",
  filtroBusqueda:  "",
  filtroTipo:      "",
  filtroEscenario: "",
  HORA_INICIO: 8,
  HORA_FIN:   18,
  PX_POR_HORA: 60,
};

/* ──────────────────────────────────────────────────────────
   UTILIDADES
────────────────────────────────────────────────────────── */

function parseFecha(str) {
  const [y, m, d] = str.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  const DIAS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
  const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  return {
    str, anio: y, mes: m, dia: d,
    diaSemana: DIAS[dt.getDay()],
    mesCorto: MESES[m - 1],
    label: `${DIAS[dt.getDay()]} ${d}`,
  };
}

function horaAMin(hs) {
  if (!hs) return 0;
  const [h, m] = hs.split(":").map(Number);
  return h * 60 + m;
}

function tipoClass(tipo) {
  const map = {
    "Conferencia magistral": "tipo-magistral",
    "Conferencia": "tipo-conferencia",
    "Taller": "tipo-taller",
    "Exhibición": "tipo-exhibicion",
    "Inauguración": "tipo-inauguracion",
    "Cierre del evento": "tipo-cierre",
  };
  return map[tipo] || "tipo-conferencia";
}

function diasHabiles(fi, ff) {
  const start = new Date(fi + "T00:00:00");
  const end = new Date(ff + "T00:00:00");
  const dias = [];
  let cur = new Date(start);
  while (cur <= end) {
    if (cur.getDay() !== 0 && cur.getDay() !== 6) {
      dias.push(cur.toISOString().slice(0, 10));
    }
    cur.setDate(cur.getDate() + 1);
  }
  return dias;
}

function rangoLabel(ev) {
  if (!ev) return "";
  const fi = parseFecha(ev.fecha_inicio);
  const ff = parseFecha(ev.fecha_fin);
  if (fi.mes === ff.mes && fi.anio === ff.anio) {
    return `${fi.dia}–${ff.dia} ${fi.mesCorto} ${fi.anio}`;
  }
  return `${fi.dia} ${fi.mesCorto} – ${ff.dia} ${ff.mesCorto} ${ff.anio}`;
}

/* ──────────────────────────────────────────────────────────
   CARGA DE EVENTOS
────────────────────────────────────────────────────────── */

async function cargarEventos() {
  try {
    const res = await fetch("/api/eventos");
    CalState.eventos = await res.json();
    renderSelectEventos();

    const activo = CalState.eventos.find(e => e.activo == 1);
    if (activo) {
      document.getElementById("eventoSelect").value = activo.id_evento;
      await seleccionarEvento(activo.id_evento);
    } else if (CalState.eventos.length > 0) {
      const primero = CalState.eventos[0];
      document.getElementById("eventoSelect").value = primero.id_evento;
      await seleccionarEvento(primero.id_evento);
    } else {
      mostrarSinEvento();
    }
  } catch (err) {
    console.error("[cargarEventos]", err);
    mostrarSinEvento();
  }
}

function renderSelectEventos() {
  const sel = document.getElementById("eventoSelect");
  if (!sel) return;

  if (CalState.eventos.length === 0) {
    sel.innerHTML = '<option value="">— Sin eventos —</option>';
    return;
  }

  sel.innerHTML = CalState.eventos.map(ev =>
    `<option value="${ev.id_evento}">
       ${ev.activo ? "★ " : ""}${ev.nombre}
       (${rangoLabel(ev)})
     </option>`
  ).join("");
}

async function seleccionarEvento(idEvento) {
  if (!idEvento) { mostrarSinEvento(); return; }

  try {
    console.log("=== DEPURACIÓN ===");
    console.log("ID Evento seleccionado:", idEvento);
    
    const [infoRes, sesRes, confRes] = await Promise.all([
      fetch(`/api/eventos/${idEvento}/info`),
      fetch(`/api/eventos/${idEvento}/sesiones`),
      fetch(`/api/eventos/${idEvento}/conflictos`),
    ]);
    
    console.log("Info response status:", infoRes.status);
    console.log("Sesiones response status:", sesRes.status);

    CalState.eventoActivo = await infoRes.json();
    CalState.sesionesEvento = await sesRes.json();
    CalState.conflictos = await confRes.json();
    CalState.diasHabiles = CalState.eventoActivo.dias_habiles || [];

    // Actualizar botón de publicación según el estado del evento
    actualizarBotonPublicacion(CalState.eventoActivo.publicado);

    console.log("Evento activo:", CalState.eventoActivo);
    console.log("Sesiones recibidas:", CalState.sesionesEvento.length);
    console.log("Primera sesión:", CalState.sesionesEvento[0]);
    console.log("Días hábiles:", CalState.diasHabiles);

    renderEventoMeta();
    renderConflictos();
    renderCalendario();

    if (CalState.vistaActual === "tabla" && typeof aplicarFiltrosYMostrar === "function") {
      window.todasLasSesiones = CalState.sesionesEvento;
      aplicarFiltrosYMostrar();
    }
  } catch (err) {
    console.error("[seleccionarEvento]", err);
  }
}

function mostrarSinEvento() {
  const grid = document.getElementById("calGrid");
  const load = document.getElementById("calLoading");
  if (load) load.innerHTML = '<span>Crea un evento para ver el calendario</span>';
  if (grid) grid.style.display = "none";
  const meta = document.getElementById("eventoMeta");
  if (meta) meta.innerHTML = "";
  const panel = document.getElementById("conflictAlert");
  if (panel) panel.style.display = "none";
  const calTitle = document.getElementById("calTitle");
  if (calTitle) calTitle.textContent = "Sin evento seleccionado";
}

function renderEventoMeta() {
  const ev = CalState.eventoActivo;
  const meta = document.getElementById("eventoMeta");
  if (!ev || !meta) return;

  meta.innerHTML = `
    <span class="evento-chip chip-active">
      <i class="fas fa-check-circle"></i> Activo
    </span>
    <span class="evento-chip">
      <i class="fas fa-calendar"></i> ${rangoLabel(ev)}
    </span>
    <span class="evento-chip">
      <i class="fas fa-sun"></i> ${ev.total_dias || 0} días hábiles
    </span>
    <span class="evento-chip">
      <i class="fas fa-chalkboard-teacher"></i> ${CalState.sesionesEvento.length} sesiones
    </span>
  `;
}

function renderConflictos() {
  const panel = document.getElementById("conflictAlert");
  const list = document.getElementById("conflictList");
  if (!panel) return;

  if (CalState.conflictos.length === 0) {
    panel.style.display = "none";
    return;
  }

  const title = document.getElementById("conflictTitle");
  if (title) title.textContent = `${CalState.conflictos.length} conflicto(s) detectado(s)`;
  
  list.innerHTML = CalState.conflictos.slice(0, 5).map(c => `
    <div class="conflict-item">
      ⚠ "${c.sesion_a}" y "${c.sesion_b}" en ${c.nombre_escenario}
    </div>
  `).join("");
  panel.style.display = "flex";
}

function renderCalendario() {
  const ev = CalState.eventoActivo;
  const dias = CalState.diasHabiles;
  const grid = document.getElementById("calGrid");
  const load = document.getElementById("calLoading");

  const calTitle = document.getElementById("calTitle");
  const calSubtitle = document.getElementById("calSubtitle");
  if (calTitle) calTitle.textContent = ev ? ev.nombre : "—";
  if (calSubtitle) calSubtitle.textContent = ev ? rangoLabel(ev) : "";

  if (!dias || dias.length === 0) {
    if (load) { load.innerHTML = "Sin días hábiles en el rango del evento."; load.style.display = "flex"; }
    if (grid) grid.style.display = "none";
    return;
  }

  if (load) load.style.display = "none";
  if (grid) grid.style.display = "grid";

  const nDias = dias.length;
  grid.style.gridTemplateColumns = `64px repeat(${nDias}, minmax(120px, 1fr))`;

  const horas = [];
  for (let h = CalState.HORA_INICIO; h < CalState.HORA_FIN; h++) horas.push(h);

  const idsConflicto = new Set();
  CalState.conflictos.forEach(c => {
    idsConflicto.add(c.id_sesion_a);
    idsConflicto.add(c.id_sesion_b);
  });

  const sesionesPorDia = {};
  dias.forEach(d => { sesionesPorDia[d] = []; });
  CalState.sesionesEvento.forEach(s => {
    if (sesionesPorDia[s.fecha] !== undefined) {
      sesionesPorDia[s.fecha].push(s);
    }
  });

  let html = "";
  html += `<div class="cal-day-header cal-time-col"></div>`;
  
  dias.forEach(d => {
    const fi = parseFecha(d);
    html += `<div class="cal-day-header"><span class="day-num">${fi.dia}</span>${fi.diaSemana}</div>`;
  });

  html += `<div class="cal-time-col" style="grid-row: span ${horas.length}; display:flex; flex-direction:column;">`;
  horas.forEach(h => {
    html += `<div class="cal-time-slot">${h.toString().padStart(2, "0")}:00</div>`;
  });
  html += `</div>`;

  dias.forEach(d => {
    const sesiones = sesionesPorDia[d] || [];
    html += `<div class="cal-day-col" style="grid-row: span ${horas.length}; position:relative;">`;
    
    horas.forEach(() => {
      html += `<div class="cal-hour-cell"><div class="cal-half-line"></div></div>`;
    });
    
    sesiones.forEach(s => {
      const inicioMin = horaAMin(s.hora_inicio_str || s.hora_inicio);
      const finMin = horaAMin(s.hora_fin_str || s.hora_fin);
      const baseMin = CalState.HORA_INICIO * 60;
      const top = ((inicioMin - baseMin) / 60) * CalState.PX_POR_HORA;
      const height = Math.max(((finMin - inicioMin) / 60) * CalState.PX_POR_HORA - 4, 25);
      const cls = idsConflicto.has(s.id_sesion) ? "tipo-conflicto" : tipoClass(s.tipo);
      
      html += `
        <div class="cal-session ${cls}" style="top:${top}px; height:${height}px" onclick="verDetalles(${s.id_sesion})">
          ${idsConflicto.has(s.id_sesion) ? '<span class="conflict-pip"></span>' : ''}
          <div class="s-nombre">${s.nombre_de_sesion || "Sin nombre"}</div>
        </div>`;
    });
    html += `</div>`;
  });

  grid.innerHTML = html;
}

function initViewToggle() {
  const btns = document.querySelectorAll(".view-btn");
  const tabla = document.getElementById("vistaTabla");
  const cal = document.getElementById("vistaCalendario");
  const searchWrap = document.getElementById("searchWrap");
  const mostrarGrp = document.getElementById("mostrarGroup");

  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      btns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      CalState.vistaActual = btn.dataset.view;

      if (CalState.vistaActual === "calendario") {
        if (cal) cal.style.display = "block";
        if (tabla) tabla.style.display = "none";
        if (searchWrap) searchWrap.style.display = "none";
        if (mostrarGrp) mostrarGrp.style.display = "none";
        renderCalendario();
      } else {
        if (cal) cal.style.display = "none";
        if (tabla) tabla.style.display = "block";
        if (searchWrap) searchWrap.style.display = "flex";
        if (mostrarGrp) mostrarGrp.style.display = "flex";
        if (typeof aplicarFiltrosYMostrar === "function") {
          window.todasLasSesiones = CalState.sesionesEvento;
          aplicarFiltrosYMostrar();
        }
      }
    });
  });
}

function abrirModalEvento(idEvento = null) {
  const modal = document.getElementById("modalEvento");
  if (!modal) return;
  
  const title = document.getElementById("modalEventoTitle");
  const editId = document.getElementById("eventoEditId");
  const actGrp = document.getElementById("activarGroup");

  document.getElementById("eventoNombre").value = "";
  document.getElementById("eventoFechaInicio").value = "";
  document.getElementById("eventoFechaFin").value = "";
  document.getElementById("eventoDescripcion").value = "";
  document.getElementById("eventoActivar").checked = true;
  document.getElementById("diasPreview").style.display = "none";
  
  editId.value = "";

  if (idEvento) {
    const ev = CalState.eventos.find(e => e.id_evento == idEvento);
    if (ev) {
      title.textContent = "Editar Evento";
      editId.value = idEvento;
      document.getElementById("eventoNombre").value = ev.nombre || "";
      document.getElementById("eventoFechaInicio").value = ev.fecha_inicio || "";
      document.getElementById("eventoFechaFin").value = ev.fecha_fin || "";
      document.getElementById("eventoDescripcion").value = ev.descripcion || "";
      if (actGrp) actGrp.style.display = "none";
    }
  } else {
    title.textContent = "Nuevo Evento";
    if (actGrp) actGrp.style.display = "";
  }
  modal.style.display = "flex";
}

function cerrarModalEvento() {
  const modal = document.getElementById("modalEvento");
  if (modal) modal.style.display = "none";
}

async function guardarEvento() {
  const idEvento = document.getElementById("eventoEditId").value;
  const nombre = document.getElementById("eventoNombre").value.trim();
  const fi = document.getElementById("eventoFechaInicio").value;
  const ff = document.getElementById("eventoFechaFin").value;
  const desc = document.getElementById("eventoDescripcion").value.trim();
  const activar = document.getElementById("eventoActivar").checked;

  if (!nombre || !fi || !ff) {
    Swal.fire("Error", "Completa todos los campos requeridos", "error");
    return;
  }

  const payload = { nombre, fecha_inicio: fi, fecha_fin: ff, descripcion: desc, activar };

  try {
    const url = idEvento ? `/api/eventos/${idEvento}` : "/api/eventos";
    const method = idEvento ? "PUT" : "POST";
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.success) {
      cerrarModalEvento();
      await Swal.fire({ title: "¡Listo!", text: data.message, icon: "success" });
      await cargarEventos();
      if (data.id_evento) {
        document.getElementById("eventoSelect").value = data.id_evento;
        await seleccionarEvento(data.id_evento);
      }
    } else {
      Swal.fire("Error", data.message, "error");
    }
  } catch (err) {
    console.error(err);
    Swal.fire("Error", "Error de conexión", "error");
  }
}

function actualizarDiasPreview() {
  const fi = document.getElementById("eventoFechaInicio").value;
  const ff = document.getElementById("eventoFechaFin").value;
  const box = document.getElementById("diasPreview");
  const txt = document.getElementById("diasPreviewText");
  if (!fi || !ff || !box || !txt) return;
  
  const dias = diasHabiles(fi, ff);
  if (dias.length === 0) {
    txt.textContent = "No contiene días hábiles (Lun–Vie).";
  } else {
    txt.textContent = `${dias.length} día(s) hábil(es) en el rango.`;
  }
  box.style.display = "flex";
}

function exportarPDF() {
  Swal.fire("Info", "Función PDF - Requiere configuración adicional", "info");
}

function exportarExcel() {
  Swal.fire("Info", "Función Excel - Requiere configuración adicional", "info");
}

/* ──────────────────────────────────────────────────────────
   ACTIVAR EVENTO (para el administrador)
────────────────────────────────────────────────────────── */

async function activarEvento() {
    if (!CalState.eventoActivo) {
        Swal.fire('Atención', 'Selecciona un evento primero', 'info');
        return;
    }
    
    const evento = CalState.eventoActivo;
    
    if (evento.activo == 1) {
        Swal.fire('Info', `"${evento.nombre}" ya está activo`, 'info');
        return;
    }
    
    const result = await Swal.fire({
        title: '¿Activar esta jornada?',
        html: `Vas a activar <strong>${evento.nombre}</strong><br>
               (${rangoLabel(evento)})<br><br>
               <span style="color: #c0392b;">⚠️ Las demás jornadas se desactivarán automáticamente.</span>`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#2d6e3e',
        confirmButtonText: 'Sí, activar'
    });
    
    if (result.isConfirmed) {
        try {
            const res = await fetch(`/api/eventos/${evento.id_evento}/activar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            
            if (data.success) {
                Swal.fire('¡Activado!', `"${evento.nombre}" ahora está activa`, 'success');
                await cargarEventos();
                document.getElementById("eventoSelect").value = evento.id_evento;
                await seleccionarEvento(evento.id_evento);
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Swal.fire('Error', error.message, 'error');
        }
    }
}

/* ──────────────────────────────────────────────────────────
   PUBLICAR EVENTO (para estudiantes)
────────────────────────────────────────────────────────── */

async function publicarEvento() {
    if (!CalState.eventoActivo) {
        Swal.fire('Atención', 'Selecciona un evento primero', 'info');
        return;
    }
    
    const evento = CalState.eventoActivo;
    const nuevoEstado = !evento.publicado;
    
    const result = await Swal.fire({
        title: nuevoEstado ? '¿Publicar jornada?' : '¿Ocultar jornada?',
        html: nuevoEstado 
            ? `Los estudiantes podrán ver <strong>${evento.nombre}</strong>`
            : `Los estudiantes ya no verán <strong>${evento.nombre}</strong>`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: nuevoEstado ? '#2d6e3e' : '#dc3545',
        confirmButtonText: nuevoEstado ? 'Sí, publicar' : 'Sí, ocultar'
    });
    
    if (result.isConfirmed) {
        try {
            const res = await fetch(`/api/eventos/${evento.id_evento}/publicar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ publicado: nuevoEstado })
            });
            const data = await res.json();
            
            if (data.success) {
                evento.publicado = nuevoEstado;
                actualizarBotonPublicacion(nuevoEstado);
                Swal.fire('¡Listo!', data.message, 'success');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            Swal.fire('Error', error.message, 'error');
        }
    }
}

function actualizarBotonPublicacion(estaPublicado) {
    const btn = document.getElementById('btnPublicarJornada');
    const btnText = document.getElementById('publicarBtnText');
    if (!btn) return;
    
    if (estaPublicado) {
        btn.style.background = '#dc3545';
        btn.style.color = 'white';
        btnText.innerHTML = '<i class="fas fa-eye-slash"></i> Ocultar jornada';
        btn.title = 'Los estudiantes pueden ver esta jornada';
    } else {
        btn.style.background = 'var(--dorado)';
        btn.style.color = 'var(--verde-oscuro)';
        btnText.innerHTML = '<i class="fas fa-globe-americas"></i> Publicar jornada';
        btn.title = 'Publicar para que los estudiantes vean esta jornada';
    }
}

/* ──────────────────────────────────────────────────────────
   INICIALIZACIÓN
────────────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  initViewToggle();

  const selEvento = document.getElementById("eventoSelect");
  if (selEvento) {
    selEvento.addEventListener("change", e => seleccionarEvento(e.target.value));
  }

  const btnNuevo = document.getElementById("btnNuevoEvento");
  if (btnNuevo) btnNuevo.addEventListener("click", () => abrirModalEvento(null));

  // Botón ACTIVAR jornada
  const btnActivar = document.getElementById("btnActivarEvento");
  if (btnActivar) {
    btnActivar.addEventListener("click", activarEvento);
  }

  // Botón PUBLICAR jornada
  const btnPublicar = document.getElementById("btnPublicarJornada");
  if (btnPublicar) {
    btnPublicar.addEventListener("click", publicarEvento);
  }

  const modalClose = document.getElementById("modalEventoClose");
  if (modalClose) modalClose.addEventListener("click", cerrarModalEvento);
  
  const btnCancel = document.getElementById("btnEventoCancel");
  if (btnCancel) btnCancel.addEventListener("click", cerrarModalEvento);
  
  const btnSave = document.getElementById("btnEventoSave");
  if (btnSave) btnSave.addEventListener("click", guardarEvento);

  const modal = document.getElementById("modalEvento");
  if (modal) {
    modal.addEventListener("click", e => { if (e.target === modal) cerrarModalEvento(); });
  }

  const fiInput = document.getElementById("eventoFechaInicio");
  const ffInput = document.getElementById("eventoFechaFin");
  if (fiInput) fiInput.addEventListener("change", actualizarDiasPreview);
  if (ffInput) ffInput.addEventListener("change", actualizarDiasPreview);

  const btnPdf = document.getElementById("btnExportPdf");
  if (btnPdf) btnPdf.addEventListener("click", exportarPDF);
  
  const btnExcel = document.getElementById("btnExportExcel");
  if (btnExcel) btnExcel.addEventListener("click", exportarExcel);
  
  const btnHtml = document.getElementById("btnExportHtml");
  if (btnHtml) {
    btnHtml.addEventListener("click", () => {
      if (!CalState.eventoActivo) {
        Swal.fire("Atención", "Selecciona un evento primero", "info");
        return;
      }
      window.open(`/admin/eventos/${CalState.eventoActivo.id_evento}/exportar-html`, "_blank");
    });
  }

  const dismiss = document.getElementById("conflictDismiss");
  if (dismiss) {
    dismiss.addEventListener("click", () => {
      const panel = document.getElementById("conflictAlert");
      if (panel) panel.style.display = "none";
    });
  }

  const filtroTipo = document.getElementById("selectFiltroTipo");
  if (filtroTipo) {
    filtroTipo.addEventListener("change", e => {
      CalState.filtroTipo = e.target.value;
      if (CalState.vistaActual === "calendario") renderCalendario();
    });
  }

  const filtroEscenario = document.getElementById("selectFiltroEscenario");
  if (filtroEscenario) {
    filtroEscenario.addEventListener("change", e => {
      CalState.filtroEscenario = e.target.value;
      if (CalState.vistaActual === "calendario") renderCalendario();
    });
  }

  cargarEventos();
  window.abrirModalEvento = abrirModalEvento;
});