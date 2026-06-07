// ============================================================
// FUNCIONALIDAD PARA LA PÁGINA DE PONENTES
// ============================================================

let filtroEspecialidadActual = '';

// Inicializar la página
document.addEventListener('DOMContentLoaded', function() {
    actualizarContadorPonentes();
    llenarFiltroEspecialidades();
    
    // Event listeners
    const searchInput = document.getElementById('buscarPonenteInput');
    if (searchInput) {
        searchInput.addEventListener('input', filtrarPonentes);
    }
    
    const filtroEspecialidad = document.getElementById('filtroEspecialidad');
    if (filtroEspecialidad) {
        filtroEspecialidad.addEventListener('change', function(e) {
            filtroEspecialidadActual = e.target.value;
            filtrarPonentes();
            mostrarBotonReset();
        });
    }
    
    // Tema oscuro/claro
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Navbar toggle para móvil
    const navbarToggle = document.getElementById('navbarToggle');
    if (navbarToggle) {
        navbarToggle.addEventListener('click', function() {
            const collapse = document.getElementById('navbarCollapse');
            collapse.classList.toggle('show');
        });
    }
    
    // Nombre del alumno
    const navNombre = document.getElementById('navNombre');
    const navAvatar = document.getElementById('navAvatar');
    if (window.NOMBRE_ALUMNO) {
        if (navNombre) navNombre.textContent = window.NOMBRE_ALUMNO;
        if (navAvatar) navAvatar.textContent = window.NOMBRE_ALUMNO.charAt(0).toUpperCase();
    }
});

// Función para filtrar ponentes
function filtrarPonentes() {
    const searchTerm = document.getElementById('buscarPonenteInput').value.toLowerCase();
    const cards = document.querySelectorAll('.ponente-card');
    let visibleCount = 0;
    
    cards.forEach(card => {
        const nombre = card.dataset.nombre || '';
        const especialidad = card.dataset.especialidad || '';
        
        const matchesSearch = nombre.includes(searchTerm) || especialidad.includes(searchTerm);
        const matchesEspecialidad = !filtroEspecialidadActual || especialidad.includes(filtroEspecialidadActual.toLowerCase());
        
        if (matchesSearch && matchesEspecialidad) {
            card.style.display = 'flex';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    actualizarContadorPonentes(visibleCount);
    
    const sinResultados = document.getElementById('sinResultados');
    if (sinResultados) {
        sinResultados.style.display = visibleCount === 0 ? 'flex' : 'none';
    }
}

// Actualizar contador de ponentes
function actualizarContadorPonentes(visibleCount = null) {
    const contadorSpan = document.getElementById('ponentesCount');
    if (contadorSpan) {
        if (visibleCount === null) {
            const totalCards = document.querySelectorAll('.ponente-card').length;
            contadorSpan.textContent = totalCards;
        } else {
            contadorSpan.textContent = visibleCount;
        }
    }
}

// Llenar filtro de especialidades desde los datos
function llenarFiltroEspecialidades() {
    const especialidades = new Set();
    document.querySelectorAll('.ponente-card').forEach(card => {
        const especialidad = card.dataset.especialidad;
        if (especialidad && especialidad.trim()) {
            especialidades.add(especialidad);
        }
    });
    
    const select = document.getElementById('filtroEspecialidad');
    if (select && especialidades.size > 0) {
        Array.from(especialidades).sort().forEach(esp => {
            const option = document.createElement('option');
            option.value = esp;
            option.textContent = esp.charAt(0).toUpperCase() + esp.slice(1);
            select.appendChild(option);
        });
    }
}

// Mostrar botón de reset
function mostrarBotonReset() {
    const resetBtn = document.getElementById('resetFiltrosBtn');
    if (resetBtn) {
        resetBtn.style.display = (filtroEspecialidadActual !== '') ? 'inline-flex' : 'none';
    }
}

// Limpiar todos los filtros
function limpiarFiltros() {
    const searchInput = document.getElementById('buscarPonenteInput');
    const filtroEspecialidad = document.getElementById('filtroEspecialidad');
    
    if (searchInput) searchInput.value = '';
    if (filtroEspecialidad) filtroEspecialidad.value = '';
    
    filtroEspecialidadActual = '';
    filtrarPonentes();
    mostrarBotonReset();
}

// Ver detalle del ponente en modal
// Ver detalle del ponente en modal
function verDetallePonente(idPonente) {
    const ponente = window.PONENTES_DATA[idPonente];
    if (!ponente) return;
    
    const modal = document.getElementById('modalPonenteOverlay');
    const avatarLarge = document.getElementById('modalAvatarLarge');
    const nombreEl = document.getElementById('modalPonenteNombre');
    const especialidadEl = document.getElementById('modalPonenteEspecialidad');
    const bioEl = document.getElementById('modalPonenteBio');
    const sesionesSection = document.getElementById('modalSesionesSection');
    const sesionesEl = document.getElementById('modalPonenteSesiones');
    const contactoSection = document.getElementById('modalContactoSection');
    const contactoEl = document.getElementById('modalPonenteContacto');
    
    // Configurar avatar
    if (ponente.foto) {
        avatarLarge.style.backgroundImage = `url('${ponente.foto}')`;
        avatarLarge.style.backgroundSize = 'cover';
        avatarLarge.textContent = '';
    } else {
        avatarLarge.style.backgroundImage = 'none';
        avatarLarge.textContent = ponente.iniciales;
    }
    
    nombreEl.textContent = ponente.nombre_completo || 'Ponente';
    especialidadEl.textContent = ponente.perfil_profesional || 'Conferencista';
    bioEl.textContent = ponente.biografia || 'No hay biografía disponible.';
    
    // Sesiones
    if (ponente.sesiones && ponente.sesiones.length > 0) {
        sesionesSection.style.display = 'block';
        sesionesEl.innerHTML = ponente.sesiones.map(sesion => `
            <div class="sesion-item-modal">
                <strong>${sesion.nombre_de_sesion}</strong>
                <small>${sesion.tipo || 'Sesión'} • ${sesion.fecha_display || 'Fecha por confirmar'} • ${sesion.hora_display || ''}</small>
                <small>📍 ${sesion.escenario || 'Sin ubicación'}</small>
            </div>
        `).join('');
    } else {
        sesionesSection.style.display = 'none';
    }
    
    // Contacto (como no hay email en sesion, ocultamos esta sección)
    contactoSection.style.display = 'none';
    
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}
// Cerrar modal
function cerrarModalPonente() {
    const modal = document.getElementById('modalPonenteOverlay');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

function cerrarModalClick(event) {
    if (event.target === event.currentTarget) {
        cerrarModalPonente();
    }
}

// Alternar tema
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', newTheme);
    
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = newTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
    }
    
    localStorage.setItem('theme', newTheme);
}

// Cargar tema guardado
const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = savedTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
    }
}