<!DOCTYPE html>
<html lang="es" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Agenda — UES San José del Rincón</title>
    
    <!-- Fonts & Icons -->
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    
    <!-- SweetAlert2 -->
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    
    <!-- html2pdf -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    
    <!-- Styles -->
    <link rel="stylesheet" href="/static/css/base.css">
    <link rel="stylesheet" href="/static/css/alumno_agenda.css">
</head>
<body>

<!-- ============================================================
     NAVBAR RESPONSIVO
============================================================ -->
<nav class="navbar">
    <span class="navbar-brand">UES San José del Rincón</span>
    
    <button class="navbar-toggle" id="navbarToggle" aria-label="Menú">
        <i class="fas fa-bars"></i>
    </button>
    
    <div class="navbar-collapse" id="navbarCollapse">
        <div class="navbar-right">
            <a href="{{ url_for('alumno_dashboard') }}" class="nav-link-pill">
                <i class="fas fa-home"></i> Inicio
            </a>
            <a href="{{ url_for('alumno_agenda') }}" class="nav-link-pill active">
                <i class="fas fa-calendar-check"></i> Mi Agenda
            </a>
            <button class="btn-icon-nav" id="themeToggle" title="Cambiar tema">
                <i class="fas fa-moon" id="themeIcon"></i>
            </button>
            <div class="user-chip">
                <div class="avatar" id="navAvatar">A</div>
                <span class="user-name" id="navNombre">Alumno</span>
            </div>
            <a href="{{ url_for('logout') }}" class="btn-icon-nav" id="logoutBtn" title="Cerrar sesión">
                <i class="fas fa-sign-out-alt"></i>
            </a>
        </div>
    </div>
</nav>

<!-- ============================================================
     HERO
============================================================ -->
<div class="hero">
    <div class="hero-tag"><i class="fas fa-calendar-check"></i> Mi agenda personal</div>
    <h1>Mis Sesiones Registradas</h1>
    <p class="hero-sub">Gestiona y descarga el programa de las sesiones a las que te has inscrito</p>
</div>

<!-- ============================================================
     TOOLBAR + STATS
============================================================ -->
<div class="toolbar">
    <div class="toolbar-left">
        <button class="view-btn active" data-view="lista" id="btnVistaLista">
            <i class="fas fa-list"></i> Lista
        </button>
        <button class="view-btn" data-view="calendario" id="btnVistaCalendario">
            <i class="fas fa-calendar-week"></i> Calendario
        </button>
    </div>
    <button class="btn-pdf" id="btnDescargarPDF">
        <i class="fas fa-file-pdf"></i> Descargar agenda PDF
    </button>
</div>

<div class="stats-bar">
    <div class="stat-chip">
        <i class="fas fa-layer-group"></i>
        <strong id="contTotal">0</strong> sesiones registradas
    </div>
    <div class="stat-chip" id="chipEvento" style="display: none;">
        <i class="fas fa-calendar"></i>
        <span id="spanEvento">—</span>
    </div>
</div>

<!-- ============================================================
     VISTA LISTA
============================================================ -->
<div id="vistaLista">
    <div class="lista-wrapper" id="listaContenedor">
        <!-- El contenido se genera con JS -->
    </div>
</div>

<!-- ============================================================
     VISTA CALENDARIO
============================================================ -->
<div id="vistaCalendario" style="display: none;">
    <div class="cal-wrapper">
        <div class="cal-scroll">
            <div class="cal-inner" id="calGrid">
                <!-- El contenido se genera con JS -->
            </div>
        </div>
    </div>
</div>

<!-- ============================================================
     MODAL DETALLE
============================================================ -->
<div class="modal-overlay" id="modalOverlay" onclick="cerrarModalClick(event)">
    <div class="modal-box">
        <div class="modal-head" id="modalHead"></div>
        <div class="modal-content">
            <button class="modal-close" onclick="cerrarModal()" title="Cerrar">&times;</button>
            <div class="modal-tipo" id="modalTipo"></div>
            <h2 class="modal-titulo" id="modalTitulo">—</h2>

            <div class="modal-ponente-row">
                <div class="modal-ponente-avatar" id="modalAvatar">??</div>
                <div>
                    <div style="font-weight:700; color:var(--texto-oscuro); margin-bottom:.2rem;" id="modalPonenteNombre">—</div>
                    <div style="font-size:.82rem; color:var(--texto-suave);" id="modalPerfil">—</div>
                </div>
            </div>

            <div class="modal-grid">
                <div class="modal-dato">
                    <div class="modal-dato-label"><i class="far fa-calendar"></i> Fecha</div>
                    <div class="modal-dato-val" id="modalFecha">—</div>
                </div>
                <div class="modal-dato">
                    <div class="modal-dato-label"><i class="far fa-clock"></i> Horario</div>
                    <div class="modal-dato-val" id="modalHorario">—</div>
                </div>
                <div class="modal-dato">
                    <div class="modal-dato-label"><i class="fas fa-map-marker-alt"></i> Escenario</div>
                    <div class="modal-dato-val" id="modalEscenario">—</div>
                </div>
                <div class="modal-dato">
                    <div class="modal-dato-label"><i class="fas fa-users"></i> Cupo</div>
                    <div class="modal-dato-val" id="modalCupo">—</div>
                </div>
            </div>

            <div class="modal-section" id="modalBioSection" style="display:none;">
                <div class="modal-section-label">Biografía del ponente</div>
                <div class="modal-section-body" id="modalBio"></div>
            </div>

            <button class="btn-quitar-modal" id="btnQuitarModal" onclick="quitarDesdeModal()">
                <i class="fas fa-heart-broken"></i> Quitar de mi agenda
            </button>
        </div>
    </div>
</div>

<!-- ============================================================
     PDF PRINTABLE
============================================================ -->
<div id="pdfTarget"></div>

<!-- ============================================================
     FOOTER
============================================================ -->
<footer>
    <strong>© 2026 UES San José del Rincón</strong><br>
    Jornada académica y cultural<br>
    Todos los derechos reservados.
</footer>

<!-- ============================================================
     SCRIPTS
============================================================ -->
<script>
    // Datos embebidos del servidor
    window.NOMBRE_ALUMNO = {{ nombre | tojson }};
    window.EVENTO_NOMBRE = {{ evento_nombre | tojson }};
    window.SESIONES_INSCRITAS = {{ sesiones_json | safe }};
    
    // Actualizar avatar
    (function() {
        const avatarEl = document.getElementById('navAvatar');
        const nombreEl = document.getElementById('navNombre');
        const nombre = window.NOMBRE_ALUMNO;
        if (nombreEl && nombre) {
            nombreEl.textContent = nombre;
            const partes = nombre.split(' ').filter(Boolean);
            if (avatarEl) {
                avatarEl.textContent = (partes[0][0] + (partes[1] ? partes[1][0] : '')).toUpperCase();
            }
        }
    })();
</script>

<script src="/static/js/global.js"></script>
<script src="/static/js/alumno_agenda.js"></script>
</body>
</html>