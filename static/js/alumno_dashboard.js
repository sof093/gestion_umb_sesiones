// ============================================================
// ALUMNO DASHBOARD JS
// ============================================================

// ── Variables globales ─────────────────────────────────────────
let inscripciones = new Set();
let sesionModalActual = null;

// Colores por tipo de sesión
const ACC_MAP = {
    'magistral': '#1a3a2a',
    'conferencia': '#1a6a8a',
    'taller': '#c8a84b',
    'exhibi': '#7a4a8a',
    'panel': '#6a4a2a',
    'cierre': '#8a2a2a',
    'inaugur': '#2d5a3d',
};

function getColor(tipo) {
    const t = tipo.toLowerCase();
    for (const [key, col] of Object.entries(ACC_MAP)) {
        if (t.includes(key)) return col;
    }
    return '#4a7a5a';
}

// ── Avatar del navbar ──────────────────────────────────────────
function actualizarAvatar(nombre) {
    const avatarEl = document.getElementById('navAvatar');
    const nombreEl = document.getElementById('navNombre');
    
    if (nombreEl && nombre) {
        nombreEl.textContent = nombre;
        const partes = nombre.split(' ').filter(Boolean);
        avatarEl.textContent = (partes[0][0] + (partes[1] ? partes[1][0] : '')).toUpperCase();
    }
}

// ── Cargar inscripciones del alumno ────────────────────────────
async function cargarInscripciones() {
    try {
        const response = await fetch('/alumno/inscripciones');
        const data = await response.json();
        if (data.success) {
            inscripciones = new Set(data.inscritas.map(id => parseInt(id)));
            actualizarCorazones();
        }
    } catch (error) {
        console.error('Error al cargar inscripciones:', error);
    }
}

// ── Actualizar corazones en la UI ──────────────────────────────
function actualizarCorazones() {
    document.querySelectorAll('.btn-fav').forEach(btn => {
        const sesionId = parseInt(btn.dataset.id);
        if (inscripciones.has(sesionId)) {
            btn.classList.add('activo');
            btn.innerHTML = '<i class="fas fa-heart"></i>';
        } else {
            btn.classList.remove('activo');
            btn.innerHTML = '<i class="far fa-heart"></i>';
        }
    });
}

// ── Inscribir ──────────────────────────────────────────────────
async function inscribir(sesionId, btnElement) {
    try {
        const response = await fetch(`/alumno/inscribir/${sesionId}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            inscripciones.add(sesionId);
            actualizarCorazones();
            
            await Swal.fire({
                title: '¡Inscripción exitosa!',
                text: data.message,
                icon: 'success',
                confirmButtonColor: '#2d5a3d',
                timer: 3000,
                timerProgressBar: true
            });
        } else {
            await Swal.fire({
                title: 'Error',
                text: data.message,
                icon: 'error',
                confirmButtonColor: '#2d5a3d'
            });
        }
    } catch (error) {
        console.error('Error:', error);
        await Swal.fire({
            title: 'Error de conexión',
            text: 'No se pudo completar la inscripción',
            icon: 'error',
            confirmButtonColor: '#2d5a3d'
        });
    }
}

// ── Desinscribir ────────────────────────────────────────────────
async function desinscribir(sesionId, btnElement) {
    try {
        const response = await fetch(`/alumno/desinscribir/${sesionId}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            inscripciones.delete(sesionId);
            actualizarCorazones();
            
            await Swal.fire({
                title: 'Sesión eliminada',
                text: data.message,
                icon: 'info',
                confirmButtonColor: '#2d5a3d',
                timer: 2500,
                timerProgressBar: true
            });
        } else {
            await Swal.fire({
                title: 'Error',
                text: data.message,
                icon: 'error',
                confirmButtonColor: '#2d5a3d'
            });
        }
    } catch (error) {
        console.error('Error:', error);
        await Swal.fire({
            title: 'Error de conexión',
            text: 'No se pudo eliminar la sesión',
            icon: 'error',
            confirmButtonColor: '#2d5a3d'
        });
    }
}

// ── Toggle inscripción (confirmación) ──────────────────────────
async function toggleInscripcion(btnElement) {
    const sesionId = parseInt(btnElement.dataset.id);
    const estaInscrito = inscripciones.has(sesionId);
    const sesion = window.SESIONES_DATA ? window.SESIONES_DATA[sesionId] : null;
    
    if (!sesion) return;
    
    if (estaInscrito) {
        const result = await Swal.fire({
            title: '¿Quitar de tu agenda?',
            text: `¿Estás seguro de que deseas eliminar "${sesion.titulo}" de tu agenda?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#e74c3c',
            cancelButtonColor: '#2d5a3d',
            confirmButtonText: 'Sí, quitar',
            cancelButtonText: 'Cancelar'
        });
        
        if (result.isConfirmed) {
            await desinscribir(sesionId, btnElement);
        }
    } else {
        const result = await Swal.fire({
            title: '¿Inscribirte a esta sesión?',
            html: `
                <div style="text-align: left;">
                    <p><strong>Sesión:</strong> ${sesion.titulo}</p>
                    <p><strong>Fecha:</strong> ${sesion.fecha}</p>
                    <p><strong>Horario:</strong> ${sesion.inicio} - ${sesion.fin}</p>
                    <p><strong>Escenario:</strong> ${sesion.escenario}</p>
                </div>
            `,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#2d5a3d',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Sí, inscribirme',
            cancelButtonText: 'Cancelar'
        });
        
        if (result.isConfirmed) {
            await inscribir(sesionId, btnElement);
        }
    }
}

// ── Búsqueda y filtrado ────────────────────────────────────────
function configurarFiltros() {
    const buscarInput = document.getElementById('buscarInput');
    const filtroTipo = document.getElementById('filtroTipo');
    const sinResultados = document.getElementById('sinResultados');

    function filtrar() {
        const q = buscarInput ? buscarInput.value.toLowerCase() : '';
        const tipo = filtroTipo ? filtroTipo.value : '';
        const cards = document.querySelectorAll('.card');
        let visibles = 0;

        cards.forEach(card => {
            const matchQ = !q || card.dataset.titulo.includes(q) || card.dataset.ponente.includes(q);
            const matchTipo = !tipo || card.dataset.tipo === tipo;
            const visible = matchQ && matchTipo;
            card.style.display = visible ? '' : 'none';
            if (visible) visibles++;
        });

        if (sinResultados) {
            sinResultados.style.display = visibles === 0 ? 'block' : 'none';
        }
    }

    if (buscarInput) buscarInput.addEventListener('input', filtrar);
    if (filtroTipo) filtroTipo.addEventListener('change', filtrar);
}

// ── Modal detalle ──────────────────────────────────────────────
function abrirModal(id) {
    const d = window.SESIONES_DATA ? window.SESIONES_DATA[id] : null;
    if (!d) return;

    sesionModalActual = id;
    
    document.getElementById('modalTitulo').textContent = d.titulo;
    document.getElementById('modalTipo').innerHTML = `<span class="tipo-badge">${d.tipo}</span>`;
    document.getElementById('modalAvatar').textContent = d.iniciales;
    document.getElementById('modalPonenteNombre').textContent = d.ponente.trim() || 'Ponente no asignado';
    document.getElementById('modalPerfil').textContent = d.perfil || 'Sin perfil registrado';
    document.getElementById('modalFecha').textContent = d.fecha;
    document.getElementById('modalHorario').textContent = `${d.inicio} – ${d.fin}`;
    document.getElementById('modalEscenario').textContent = d.escenario;
    document.getElementById('modalCupo').textContent = `${d.cupo} personas`;

    const bioSec = document.getElementById('modalBioSection');
    if (d.bio) {
        document.getElementById('modalBio').textContent = d.bio;
        bioSec.style.display = '';
    } else {
        bioSec.style.display = 'none';
    }

    const color = getColor(d.tipo);
    document.getElementById('modalHead').style.background = color;
    document.getElementById('modalAvatar').style.background = color;
    
    const btnQuitar = document.getElementById('btnQuitarModal');
    if (btnQuitar) {
        btnQuitar.style.display = inscripciones.has(parseInt(id)) ? 'block' : 'none';
    }

    document.getElementById('modalOverlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function cerrarModal() {
    document.getElementById('modalOverlay').classList.remove('open');
    document.body.style.overflow = '';
    sesionModalActual = null;
}

function cerrarModalClick(e) {
    if (e.target === document.getElementById('modalOverlay')) cerrarModal();
}

async function quitarInscripcionModal() {
    if (!sesionModalActual) return;
    cerrarModal();
    
    const btn = document.querySelector(`.btn-fav[data-id="${sesionModalActual}"]`);
    if (btn) {
        await desinscribir(sesionModalActual, btn);
    }
}

// ── Inicializar ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const nombre = window.NOMBRE_ALUMNO;
    actualizarAvatar(nombre);
    cargarInscripciones();
    configurarFiltros();
    
    // Eventos de teclado para modal
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') cerrarModal();
    });
    
    // Exponer funciones globales
    window.abrirModal = abrirModal;
    window.cerrarModal = cerrarModal;
    window.cerrarModalClick = cerrarModalClick;
    window.toggleInscripcion = toggleInscripcion;
    window.quitarInscripcionModal = quitarInscripcionModal;
});
