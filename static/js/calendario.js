// ============================================================
//  calendario.js — UES San José del Rincón
//  Vista de calendario semanal, gestión de eventos,
//  detección de conflictos, exportación PDF/Excel/HTML.
//
//  Depende de:
//    • SweetAlert2  (Swal)
//    • jsPDF        (window.jspdf.jsPDF)
//    • jsPDF-AutoTable
//    • SheetJS      (XLSX)
//  Todos se cargan en admin_sesiones.html antes de este script.
// ============================================================

"use strict";

/* ──────────────────────────────────────────────────────────
   ESTADO GLOBAL
────────────────────────────────────────────────────────── */
const CalState = {
  eventos:         [],      // todos los eventos
  eventoActivo:    null,    // objeto evento seleccionado
  sesionesEvento:  [],      // sesiones del evento activo
  conflictos:      [],      // pares en conflicto
  diasHabiles:     [],      // ["2026-11-10", …]
  vistaActual:     "calendario",  // "calendario" | "tabla"

  // Filtros (compartidos con la vista tabla)
  filtroBusqueda:  "",
  filtroTipo:      "",
  filtroEscenario: "",

  HORA_INICIO: 8,   // primera hora visible
  HORA_FIN:   18,   // última hora visible (exclusive)
  PX_POR_HORA: 60,  // altura en px de cada hora
};

/* ──────────────────────────────────────────────────────────
   UTILIDADES
────────────────────────────────────────────────────────── */

/** "2026-11-10" → {anio,mes,dia,label corto,label largo} */
function parseFecha(str) {
  const [y, m, d] = str.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  const DIAS  = ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"];
  const MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
  const MESES_L = ["enero","febrero","marzo","abril","mayo","junio",
                   "julio","agosto","septiembre","octubre","noviembre","diciembre"];
  return {
    str, anio: y, mes: m, dia: d,
    diaSemana: DIAS[dt.getDay()],
    mesCorto:  MESES[m - 1],
    mesLargo:  MESES_L[m - 1],
    label:     `${DIAS[dt.getDay()]} ${d}`,
    labelLargo:`${DIAS[dt.getDay()]} ${d} de ${MESES_L[m - 1]}`,
  };
}

/** "08:30" → minutos desde medianoche */
function horaAMin(hs) {
  if (!hs) return 0;
  const [h, m] = hs.split(":").map(Number);
  return h * 60 + m;
}

/** Clase CSS de tipo de sesión */
function tipoClass(tipo) {
  const map = {
    "Conferencia magistral": "tipo-magistral",
    "Conferencia":           "tipo-conferencia",
    "Taller":                "tipo-taller",
    "Exhibición":            "tipo-exhibicion",
    "Inauguración":          "tipo-inauguracion",
    "Cierre del evento":     "tipo-cierre",
  };
  return map[tipo] || "tipo-conferencia";
}

/** Días hábiles entre dos fechas (sin fines de semana) */
function diasHabiles(fi, ff) {
  const start = new Date(fi + "T00:00:00");
  const end   = new Date(ff + "T00:00:00");
  const dias  = [];
  let cur     = new Date(start);
  while (cur <= end) {
    if (cur.getDay() !== 0 && cur.getDay() !== 6) {
      dias.push(cur.toISOString().slice(0, 10));
    }
    cur.setDate(cur.getDate() + 1);
  }
  return dias;
}

/** Formatea rango de fechas: "10–14 Nov 2026" */
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
    const res  = await fetch("/api/eventos");
    CalState.eventos = await res.json();
    renderSelectEventos();

    // Seleccionar el evento activo por defecto
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

  // Obtener info completa del evento (incluye dias_habiles)
  try {
    const [infoRes, sesRes, confRes] = await Promise.all([
      fetch(`/api/eventos/${idEvento}/info`),
      fetch(`/api/eventos/${idEvento}/sesiones`),
      fetch(`/api/eventos/${idEvento}/conflictos`),
    ]);

    CalState.eventoActivo   = await infoRes.json();
    CalState.sesionesEvento = await sesRes.json();
    CalState.conflictos     = await confRes.json();
    CalState.diasHabiles    = CalState.eventoActivo.dias_habiles || [];

    renderEventoMeta();
    renderConflictos();
    renderCalendario();

    // También refrescar vista tabla si está activa
    if (CalState.vistaActual === "tabla") {
      if (typeof aplicarFiltrosYMostrar === "function") aplicarFiltrosYMostrar();
    }
  } catch (err) {
    console.error("[seleccionarEvento]", err);
  }
}

function mostrarSinEvento() {
  const grid = document.getElementById("calGrid");
  const load = document.getElementById("calLoading");
  if (load) load.innerHTML = '<span style="color:var(--texto-medio)">Crea un evento para ver el calendario</span>';
  if (grid) grid.style.display = "none";
  document.getElementById("eventoMeta").innerHTML = "";
  document.getElementById("conflictAlert").style.display = "none";
  document.getElementById("calTitle").textContent = "Sin evento seleccionado";
  document.getElementById("calSubtitle").textContent = "";
}

function renderEventoMeta() {
  const ev  = CalState.eventoActivo;
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
      <i class="fas fa-sun"></i> ${ev.total_dias} días hábiles
    </span>
    <span class="evento-chip">
      <i class="fas fa-chalkboard-teacher"></i> ${CalState.sesionesEvento.length} sesiones
    </span>
  `;
}

/* ──────────────────────────────────────────────────────────
   CONFLICTOS
────────────────────────────────────────────────────────── */

function renderConflictos() {
  const panel = document.getElementById("conflictAlert");
  const title = document.getElementById("conflictTitle");
  const list  = document.getElementById("conflictList");
  if (!panel) return;

  if (CalState.conflictos.length === 0) {
    panel.style.display = "none";
    return;
  }

  title.textContent = `${CalState.conflictos.length} conflicto(s) detectado(s)`;
  list.innerHTML = CalState.conflictos.slice(0, 5).map(c => {
    const fi = parseFecha(c.fecha);
    return `<div class="conflict-item">
      <i class="fas fa-dot-circle" style="font-size:.6rem;margin-right:.3rem"></i>
      <strong>${c.nombre_escenario}</strong> · ${fi.labelLargo} ·
      "${c.sesion_a}" (${c.inicio_a_str || c.inicio_a}–${c.fin_a_str || c.fin_a})
      y "${c.sesion_b}" (${c.inicio_b_str || c.inicio_b}–${c.fin_b_str || c.fin_b})
    </div>`;
  }).join("");

  if (CalState.conflictos.length > 5) {
    list.innerHTML += `<div style="font-size:.8rem;margin-top:.3rem;opacity:.7">
      … y ${CalState.conflictos.length - 5} conflicto(s) más
    </div>`;
  }

  panel.style.display = "flex";
}

/* ──────────────────────────────────────────────────────────
   RENDER DEL CALENDARIO
────────────────────────────────────────────────────────── */

function renderCalendario() {
  const ev   = CalState.eventoActivo;
  const dias = CalState.diasHabiles;
  const grid = document.getElementById("calGrid");
  const load = document.getElementById("calLoading");

  // Título del calendario
  document.getElementById("calTitle").textContent =
    ev ? ev.nombre : "—";
  document.getElementById("calSubtitle").textContent =
    ev ? rangoLabel(ev) : "";

  if (!dias || dias.length === 0) {
    if (load) { load.innerHTML = "Sin días hábiles en el rango del evento."; load.style.display = "flex"; }
    if (grid) grid.style.display = "none";
    return;
  }

  if (load) load.style.display = "none";
  if (grid) grid.style.display = "grid";

  // Set grid-template-columns: hora-col + N días
  const nDias = dias.length;
  grid.style.gridTemplateColumns = `64px repeat(${nDias}, minmax(120px, 1fr))`;

  // Horas visibles: 8,9,…17
  const horas = [];
  for (let h = CalState.HORA_INICIO; h < CalState.HORA_FIN; h++) horas.push(h);

  // IDs con conflicto
  const idsConflicto = new Set();
  CalState.conflictos.forEach(c => {
    idsConflicto.add(c.id_sesion_a);
    idsConflicto.add(c.id_sesion_b);
  });

  // Agrupar sesiones por fecha
  const sesionesPorDia = {};
  dias.forEach(d => { sesionesPorDia[d] = []; });
  CalState.sesionesEvento.forEach(s => {
    if (sesionesPorDia[s.fecha] !== undefined) {
      sesionesPorDia[s.fecha].push(s);
    }
  });

  // Aplicar filtros de tipo y escenario
  function sesionVisible(s) {
    if (CalState.filtroTipo      && s.tipo            !== CalState.filtroTipo)      return false;
    if (CalState.filtroEscenario && s.escenario_nombre !== CalState.filtroEscenario) return false;
    return true;
  }

  // Hoy
  const hoy = new Date().toISOString().slice(0, 10);

  let html = "";

  // ── Fila de cabeceras ──
  // Celda vacía (esquina)
  html += `<div class="cal-day-header cal-time-col" style="border-bottom:2px solid var(--gris-tabla);background:var(--gris-fondo)"></div>`;

  dias.forEach(d => {
    const fi = parseFecha(d);
    const esHoy = d === hoy;
    html += `<div class="cal-day-header${esHoy ? " hoy" : ""}">
      <span class="day-num">${fi.dia}</span>
      ${fi.diaSemana}
    </div>`;
  });

  // ── Columna de horas + celdas de días ──
  // Estrategia: generamos la columna de horas y las columnas de días
  // usando un layout que mezcla la fila de cabecera + el body.
  // El body es un sub-grid manual: cada columna es un div apilado.

  // Primero la columna de tiempo
  html += `<div class="cal-time-col" style="grid-row: span ${horas.length}; display:flex; flex-direction:column;">`;
  horas.forEach(h => {
    html += `<div class="cal-time-slot">${h.toString().padStart(2,"0")}:00</div>`;
  });
  html += `</div>`;

  // Luego cada columna de día
  dias.forEach(d => {
    const sesiones = (sesionesPorDia[d] || []).filter(sesionVisible);
    html += `<div class="cal-day-col" style="grid-row: span ${horas.length}; position:relative;">`;

    // Celdas de hora (fondo)
    horas.forEach(() => {
      html += `<div class="cal-hour-cell"><div class="cal-half-line"></div></div>`;
    });

    // Sesiones posicionadas absolutamente
    sesiones.forEach(s => {
      const inicioMin = horaAMin(s.hora_inicio_str || s.hora_inicio);
      const finMin    = horaAMin(s.hora_fin_str    || s.hora_fin);
      const baseMin   = CalState.HORA_INICIO * 60;
      const top       = ((inicioMin - baseMin) / 60) * CalState.PX_POR_HORA;
      const height    = Math.max(((finMin - inicioMin) / 60) * CalState.PX_POR_HORA - 4, 20);
      const esConfl   = idsConflicto.has(s.id_sesion);
      const cls       = esConfl ? "tipo-conflicto" : tipoClass(s.tipo);
      const ponente   = `${s.nombre_ponente || ""} ${s.apellido_paterno || ""}`.trim();

      html += `
        <div class="cal-session ${cls}"
             style="top:${top}px; height:${height}px"
             onclick="verDetalles(${s.id_sesion})"
             title="${s.nombre_de_sesion} · ${s.hora_inicio_str || s.hora_inicio}–${s.hora_fin_str || s.hora_fin}">
          ${esConfl ? '<span class="conflict-pip"></span>' : ""}
          <div class="s-nombre">${s.nombre_de_sesion || "Sin nombre"}</div>
          ${height > 32 ? `<div class="s-hora">${s.hora_inicio_str || s.hora_inicio}–${s.hora_fin_str || s.hora_fin}</div>` : ""}
          ${height > 48 && ponente ? `<div class="s-escenario">${ponente}</div>` : ""}
          ${height > 60 && s.escenario_nombre ? `<div class="s-escenario">${s.escenario_nombre}</div>` : ""}
        </div>`;
    });

    html += `</div>`;
  });

  grid.innerHTML = html;
}

/* ──────────────────────────────────────────────────────────
   TOGGLE DE VISTA
────────────────────────────────────────────────────────── */

function initViewToggle() {
  const btns = document.querySelectorAll(".view-btn");
  const tabla = document.getElementById("vistaTabla");
  const cal   = document.getElementById("vistaCalendario");
  const searchWrap  = document.getElementById("searchWrap");
  const mostrarGrp  = document.getElementById("mostrarGroup");

  btns.forEach(btn => {
    btn.addEventListener("click", () => {
      btns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      CalState.vistaActual = btn.dataset.view;

      if (CalState.vistaActual === "calendario") {
        cal.style.display   = "";
        tabla.style.display = "none";
        searchWrap.style.display  = "none";
        mostrarGrp.style.display  = "none";
        renderCalendario();
      } else {
        cal.style.display   = "none";
        tabla.style.display = "";
        searchWrap.style.display  = "";
        mostrarGrp.style.display  = "";
        // Sobrescribir todasLasSesiones con las del evento activo
        if (typeof aplicarFiltrosYMostrar === "function") {
          // Exponer las sesiones del evento al módulo de tabla
          window.todasLasSesiones = CalState.sesionesEvento;
          aplicarFiltrosYMostrar();
        }
      }
    });
  });
}

/* ──────────────────────────────────────────────────────────
   MODAL CREAR / EDITAR EVENTO
────────────────────────────────────────────────────────── */

function abrirModalEvento(idEvento = null) {
  const modal  = document.getElementById("modalEvento");
  const title  = document.getElementById("modalEventoTitle");
  const editId = document.getElementById("eventoEditId");
  const chkAct = document.getElementById("eventoActivar");
  const actGrp = document.getElementById("activarGroup");

  limpiarModalEvento();

  if (idEvento) {
    // Modo edición
    const ev = CalState.eventos.find(e => e.id_evento == idEvento);
    if (!ev) return;
    title.textContent = "Editar Evento";
    editId.value = idEvento;
    document.getElementById("eventoNombre").value       = ev.nombre || "";
    document.getElementById("eventoFechaInicio").value  = ev.fecha_inicio || "";
    document.getElementById("eventoFechaFin").value     = ev.fecha_fin    || "";
    document.getElementById("eventoDescripcion").value  = ev.descripcion  || "";
    actGrp.style.display = "none"; // No mostramos "activar" en edición
    actualizarDiasPreview();
  } else {
    title.textContent = "Nuevo Evento";
    actGrp.style.display = "";
  }

  modal.style.display = "flex";
}

function cerrarModalEvento() {
  document.getElementById("modalEvento").style.display = "none";
  limpiarModalEvento();
}

function limpiarModalEvento() {
  document.getElementById("eventoEditId").value       = "";
  document.getElementById("eventoNombre").value       = "";
  document.getElementById("eventoFechaInicio").value  = "";
  document.getElementById("eventoFechaFin").value     = "";
  document.getElementById("eventoDescripcion").value  = "";
  document.getElementById("eventoActivar").checked    = true;
  document.getElementById("diasPreview").style.display = "none";
  ["err-nombre","err-fi","err-ff"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });
}

function actualizarDiasPreview() {
  const fi  = document.getElementById("eventoFechaInicio").value;
  const ff  = document.getElementById("eventoFechaFin").value;
  const box = document.getElementById("diasPreview");
  const txt = document.getElementById("diasPreviewText");

  if (!fi || !ff) { box.style.display = "none"; return; }

  const dias = diasHabiles(fi, ff);
  if (dias.length === 0) {
    txt.textContent = "El rango seleccionado no contiene días hábiles (Lun–Vie).";
    box.style.background = "rgba(192,57,43,.08)";
    box.style.borderColor = "rgba(192,57,43,.25)";
    box.style.color = "#c0392b";
  } else {
    const fi2 = parseFecha(dias[0]);
    const ff2 = parseFecha(dias[dias.length - 1]);
    txt.textContent = `${dias.length} día(s) hábil(es): ${fi2.labelLargo} al ${ff2.labelLargo}`;
    box.style.background = "";
    box.style.borderColor = "";
    box.style.color = "";
  }
  box.style.display = "flex";
}

async function guardarEvento() {
  const idEvento = document.getElementById("eventoEditId").value;
  const nombre   = document.getElementById("eventoNombre").value.trim();
  const fi       = document.getElementById("eventoFechaInicio").value;
  const ff       = document.getElementById("eventoFechaFin").value;
  const desc     = document.getElementById("eventoDescripcion").value.trim();
  const activar  = document.getElementById("eventoActivar").checked;

  // Validación cliente
  let ok = true;
  function showErr(id, msg) {
    const el = document.getElementById(id);
    if (el) { el.textContent = msg; el.style.display = "block"; }
    ok = false;
  }
  ["err-nombre","err-fi","err-ff"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });

  if (!nombre)       showErr("err-nombre", "El nombre es requerido");
  if (!fi)           showErr("err-fi",     "La fecha inicio es requerida");
  if (!ff)           showErr("err-ff",     "La fecha fin es requerida");
  if (fi && ff && ff < fi) showErr("err-ff", "La fecha fin no puede ser anterior a la inicio");
  if (fi && ff && diasHabiles(fi, ff).length === 0)
    showErr("err-ff", "No hay días hábiles en el rango seleccionado");

  if (!ok) return;

  const payload = { nombre, fecha_inicio: fi, fecha_fin: ff, descripcion: desc, activar };

  try {
    const url    = idEvento ? `/api/eventos/${idEvento}` : "/api/eventos";
    const method = idEvento ? "PUT" : "POST";
    const res    = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.success) {
      cerrarModalEvento();
      await Swal.fire({
        title: "¡Listo!",
        text: data.message || "Evento guardado",
        icon: "success",
        confirmButtonColor: "#2d6e3e",
      });
      await cargarEventos();

      // Seleccionar el nuevo evento en el select
      if (data.id_evento) {
        document.getElementById("eventoSelect").value = data.id_evento;
        await seleccionarEvento(data.id_evento);
      }
    } else {
      Swal.fire({ title: "Error", text: data.message, icon: "error", confirmButtonColor: "#2d6e3e" });
    }
  } catch (err) {
    console.error("[guardarEvento]", err);
    Swal.fire({ title: "Error", text: "Error de conexión", icon: "error" });
  }
}

/* ──────────────────────────────────────────────────────────
   EXPORTACIÓN — PDF
────────────────────────────────────────────────────────── */

function exportarPDF() {
  const ev = CalState.eventoActivo;
  if (!ev) { Swal.fire("Atención", "Selecciona un evento primero", "info"); return; }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });

  // Encabezado
  doc.setFillColor(26, 58, 42);
  doc.rect(0, 0, 297, 22, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.text("UES San José del Rincón", 14, 10);
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text(`Itinerario — ${ev.nombre}  |  ${rangoLabel(ev)}`, 14, 17);

  // Tabla de sesiones
  const sesiones = [...CalState.sesionesEvento].sort((a, b) => {
    if (a.fecha < b.fecha) return -1;
    if (a.fecha > b.fecha) return 1;
    return (a.hora_inicio_str || a.hora_inicio) < (b.hora_inicio_str || b.hora_inicio) ? -1 : 1;
  });

  const idsConflicto = new Set();
  CalState.conflictos.forEach(c => {
    idsConflicto.add(c.id_sesion_a);
    idsConflicto.add(c.id_sesion_b);
  });

  const rows = sesiones.map(s => {
    const fi = parseFecha(s.fecha);
    const ponente = `${s.nombre_ponente || ""} ${s.apellido_paterno || ""}`.trim();
    return [
      `${fi.diaSemana} ${fi.dia} ${fi.mesCorto}`,
      `${s.hora_inicio_str || s.hora_inicio} – ${s.hora_fin_str || s.hora_fin}`,
      s.nombre_de_sesion || "—",
      ponente || "—",
      s.tipo || "—",
      s.escenario_nombre || "—",
      idsConflicto.has(s.id_sesion) ? "⚠ Conflicto" : "OK",
    ];
  });

  doc.autoTable({
    startY: 26,
    head: [["Fecha", "Horario", "Sesión", "Ponente", "Tipo", "Escenario", "Estado"]],
    body: rows,
    styles: { fontSize: 8, cellPadding: 3 },
    headStyles: { fillColor: [26, 58, 42], textColor: 255, fontStyle: "bold" },
    columnStyles: { 6: { cellWidth: 22 } },
    alternateRowStyles: { fillColor: [244, 246, 243] },
    didParseCell(data) {
      if (data.column.index === 6 && data.cell.text[0] === "⚠ Conflicto") {
        data.cell.styles.textColor = [192, 57, 43];
        data.cell.styles.fontStyle = "bold";
      }
    },
  });

  // Pie
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setTextColor(150);
    doc.text(
      `Página ${i} de ${pageCount}  ·  Generado el ${new Date().toLocaleDateString("es-MX")}`,
      148, doc.internal.pageSize.height - 5,
      { align: "center" }
    );
  }

  doc.save(`Itinerario_${ev.nombre.replace(/\s+/g, "_")}.pdf`);
}

/* ──────────────────────────────────────────────────────────
   EXPORTACIÓN — Excel
────────────────────────────────────────────────────────── */

function exportarExcel() {
  const ev = CalState.eventoActivo;
  if (!ev) { Swal.fire("Atención", "Selecciona un evento primero", "info"); return; }

  const idsConflicto = new Set();
  CalState.conflictos.forEach(c => {
    idsConflicto.add(c.id_sesion_a);
    idsConflicto.add(c.id_sesion_b);
  });

  // Hoja 1: Sesiones
  const sesiones = [...CalState.sesionesEvento].sort((a, b) => {
    if (a.fecha < b.fecha) return -1;
    if (a.fecha > b.fecha) return 1;
    return 0;
  });

  const rowsSes = sesiones.map(s => {
    const fi = parseFecha(s.fecha);
    return {
      "Fecha":     `${fi.diaSemana} ${fi.dia} de ${fi.mesLargo} ${fi.anio}`,
      "Inicio":    s.hora_inicio_str || s.hora_inicio,
      "Fin":       s.hora_fin_str    || s.hora_fin,
      "Sesión":    s.nombre_de_sesion || "",
      "Ponente":   `${s.nombre_ponente || ""} ${s.apellido_paterno || ""}`.trim(),
      "Tipo":      s.tipo || "",
      "Escenario": s.escenario_nombre || "",
      "Sede":      s.sede || "",
      "Cupo":      s.cupo_audiencia || "",
      "Estado":    idsConflicto.has(s.id_sesion) ? "CONFLICTO" : "OK",
    };
  });

  // Hoja 2: Conflictos
  const rowsConf = CalState.conflictos.map(c => ({
    "Fecha":      c.fecha,
    "Escenario":  c.nombre_escenario,
    "Sesión A":   c.sesion_a,
    "Inicio A":   c.inicio_a_str || c.inicio_a,
    "Fin A":      c.fin_a_str    || c.fin_a,
    "Sesión B":   c.sesion_b,
    "Inicio B":   c.inicio_b_str || c.inicio_b,
    "Fin B":      c.fin_b_str    || c.fin_b,
  }));

  const wb  = XLSX.utils.book_new();
  const ws1 = XLSX.utils.json_to_sheet(rowsSes);
  const ws2 = XLSX.utils.json_to_sheet(rowsConf.length ? rowsConf : [{ "Info": "Sin conflictos" }]);

  // Anchos de columna
  ws1["!cols"] = [
    { wch: 26 }, { wch: 8 }, { wch: 8 }, { wch: 36 }, { wch: 24 },
    { wch: 20 }, { wch: 22 }, { wch: 24 }, { wch: 8 }, { wch: 12 },
  ];

  XLSX.utils.book_append_sheet(wb, ws1, "Sesiones");
  XLSX.utils.book_append_sheet(wb, ws2, "Conflictos");

  XLSX.writeFile(wb, `Itinerario_${ev.nombre.replace(/\s+/g, "_")}.xlsx`);
}

/* ──────────────────────────────────────────────────────────
   INICIALIZACIÓN
────────────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {

  // ─ Toggle de vista ─
  initViewToggle();

  // ─ Selector de evento ─
  const selEvento = document.getElementById("eventoSelect");
  if (selEvento) {
    selEvento.addEventListener("change", e => {
      seleccionarEvento(e.target.value);
    });
  }

  // ─ Botón nuevo evento ─
  document.getElementById("btnNuevoEvento")?.addEventListener("click", () => {
    abrirModalEvento(null);
  });

  // ─ Modal evento ─
  document.getElementById("modalEventoClose")?.addEventListener("click", cerrarModalEvento);
  document.getElementById("btnEventoCancel")?.addEventListener("click", cerrarModalEvento);
  document.getElementById("btnEventoSave")?.addEventListener("click", guardarEvento);

  // ─ Preview días hábiles en tiempo real ─
  ["eventoFechaInicio", "eventoFechaFin"].forEach(id => {
    document.getElementById(id)?.addEventListener("change", actualizarDiasPreview);
  });

  // ─ Cerrar modal al hacer click fuera ─
  document.getElementById("modalEvento")?.addEventListener("click", e => {
    if (e.target === document.getElementById("modalEvento")) cerrarModalEvento();
  });

  // ─ Exportación ─
  document.getElementById("btnExportPdf")?.addEventListener("click", exportarPDF);
  document.getElementById("btnExportExcel")?.addEventListener("click", exportarExcel);
  document.getElementById("btnExportHtml")?.addEventListener("click", () => {
    if (!CalState.eventoActivo) { Swal.fire("Atención", "Selecciona un evento primero", "info"); return; }
    window.open(`/admin/eventos/${CalState.eventoActivo.id_evento}/exportar-html`, "_blank");
  });

  // ─ Conflictos dismiss ─
  document.getElementById("conflictDismiss")?.addEventListener("click", () => {
    document.getElementById("conflictAlert").style.display = "none";
  });

  // ─ Filtros: re-render calendario en cambio ─
  document.getElementById("selectFiltroTipo")?.addEventListener("change", e => {
    CalState.filtroTipo = e.target.value;
    if (CalState.vistaActual === "calendario") renderCalendario();
  });
  document.getElementById("selectFiltroEscenario")?.addEventListener("change", e => {
    CalState.filtroEscenario = e.target.value;
    if (CalState.vistaActual === "calendario") renderCalendario();
  });

  // ─ Carga inicial ─
  cargarEventos();

  // ─ Exponer función de edición de evento (accesible desde tabla si se necesita) ─
  window.abrirModalEvento = abrirModalEvento;
});