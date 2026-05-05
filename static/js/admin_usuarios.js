// static/js/admin_usuarios.js
// =============================================
// VARIABLES GLOBALES
// =============================================
let todosLosUsuarios = [];   // Array unificado de alumnos + admins
let currentPage      = 1;
let rowsPerPage      = 5;
let currentSearch    = '';
let currentFiltroRol = '';
let currentFiltroCarrera = '';

// =============================================
// INICIALIZACIÓN
// =============================================
document.addEventListener('DOMContentLoaded', function () {
    cargarCarreras();
    cargarUsuarios();

    document.getElementById('buscarInput').addEventListener('input', e => {
        currentSearch = e.target.value;
        currentPage   = 1;
        aplicarFiltrosYMostrar();
    });

    document.getElementById('selectFiltroRol').addEventListener('change', e => {
        currentFiltroRol = e.target.value;
        currentPage = 1;
        aplicarFiltrosYMostrar();
    });

    document.getElementById('selectFiltroCarrera').addEventListener('change', e => {
        currentFiltroCarrera = e.target.value;
        currentPage = 1;
        aplicarFiltrosYMostrar();
    });

    document.getElementById('selectMostrar').addEventListener('change', e => {
        rowsPerPage = parseInt(e.target.value);
        currentPage = 1;
        aplicarFiltrosYMostrar();
    });

    document.getElementById('btnNuevoUsuario').addEventListener('click', abrirModalNuevo);
    document.getElementById('formUsuario').addEventListener('submit', guardarUsuario);

    // Cerrar modales al clic fuera del contenedor
    ['modalVerUsuario', 'modalFormUsuario'].forEach(id => {
        document.getElementById(id).addEventListener('click', function (e) {
            if (e.target === this) this.classList.remove('open');
        });
    });
});

// =============================================
// CARGA DE DATOS
// =============================================
async function cargarUsuarios() {
    mostrarCargando();
    try {
        const res = await fetch('/api/usuarios');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        todosLosUsuarios = await res.json();
        aplicarFiltrosYMostrar();
    } catch (err) {
        console.error('Error al cargar usuarios:', err);
        document.getElementById('tablaCuerpo').innerHTML =
            `<tr><td colspan="7" class="cargando-td" style="color:#c0392b;">
                <i class="fas fa-exclamation-circle"></i> Error al cargar los usuarios
             </td></tr>`;
    }
}

async function cargarCarreras() {
    try {
        const res = await fetch('/api/carreras');
        if (!res.ok) return;
        const carreras = await res.json();

        [document.getElementById('selectFiltroCarrera'),
         document.getElementById('inputCarrera')].forEach(sel => {
            carreras.forEach(c => {
                const opt = document.createElement('option');
                opt.value       = c.id_carrera;
                opt.textContent = c.nombre_carrera;
                sel.appendChild(opt.cloneNode(true));
            });
        });
    } catch (e) {
        console.error('Error al cargar carreras:', e);
    }
}

function mostrarCargando() {
    document.getElementById('tablaCuerpo').innerHTML =
        `<tr><td colspan="7" class="cargando-td">
            <i class="fas fa-spinner fa-spin"></i> Cargando usuarios...
         </td></tr>`;
}

// =============================================
// FILTROS Y PAGINACIÓN
// =============================================
function aplicarFiltrosYMostrar() {
    let datos = [...todosLosUsuarios];

    // Búsqueda por nombre, correo o matrícula
    if (currentSearch) {
        const q = currentSearch.toLowerCase();
        datos = datos.filter(u => {
            const nombre = `${u.nombre} ${u.apellido_paterno || ''} ${u.apellido_materno || ''}`.toLowerCase();
            return nombre.includes(q)
                || (u.correo  || '').toLowerCase().includes(q)
                || (u.matricula || '').toLowerCase().includes(q);
        });
    }

    // Filtro rol
    if (currentFiltroRol) {
        datos = datos.filter(u => u.rol === currentFiltroRol);
    }

    // Filtro carrera (solo alumnos)
    if (currentFiltroCarrera) {
        datos = datos.filter(u => String(u.id_carrera) === String(currentFiltroCarrera));
    }

    const total      = datos.length;
    const totalPages = Math.max(1, Math.ceil(total / rowsPerPage));
    if (currentPage > totalPages) currentPage = totalPages;

    const inicio = (currentPage - 1) * rowsPerPage;
    const pagina = datos.slice(inicio, inicio + rowsPerPage);

    mostrarTabla(pagina, inicio, total);
    mostrarPaginacion(totalPages, total);
}

// =============================================
// RENDERIZAR TABLA
// =============================================
function mostrarTabla(usuarios, offset, totalFiltrado) {
    const tbody = document.getElementById('tablaCuerpo');

    if (!usuarios.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="cargando-td">
            <i class="fas fa-users" style="font-size:1.8rem;opacity:.25;display:block;margin-bottom:.5rem;"></i>
            No hay usuarios que coincidan con la búsqueda
        </td></tr>`;
        return;
    }

    let html = '';
    usuarios.forEach((u, i) => {
        const num    = offset + i + 1;
        const nombre = `${u.nombre} ${u.apellido_paterno || ''} ${u.apellido_materno || ''}`.trim();
        const correo = u.correo || '—';
        const mat    = u.matricula || '—';
        const carrera = u.nombre_carrera || '—';
        const rolLabel = u.rol === 'admin' ? 'Administrador' : 'Alumno';
        const rolIcon  = u.rol === 'admin' ? 'fa-user-shield' : 'fa-user-graduate';

        html += `<tr>
            <td class="num-usuario">${num}</td>
            <td><div class="usuario-nombre">${nombre}</div></td>
            <td><div class="usuario-sub">${correo}</div></td>
            <td><span class="badge-matricula">${mat}</span></td>
            <td>${u.rol === 'alumno' ? `<span class="badge-carrera">${carrera}</span>` : '<span style="color:var(--texto-claro)">—</span>'}</td>
            <td>
                <span class="badge-rol ${u.rol}">
                    <i class="fas ${rolIcon}"></i> ${rolLabel}
                </span>
            </td>
            <td class="acciones">
                <button onclick="verUsuario(${u.id}, '${u.rol}')" class="btn-icon-action view" title="Ver detalle">
                    <i class="fas fa-eye"></i>
                </button>
                <button onclick="editarUsuario(${u.id}, '${u.rol}')" class="btn-icon-action edit" title="Editar">
                    <i class="fas fa-pencil-alt"></i>
                </button>
                <button onclick="eliminarUsuario(${u.id}, '${u.rol}', '${nombre.replace(/'/g,"\\'")}') " class="btn-icon-action delete" title="Eliminar">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </td>
        </tr>`;
    });

    tbody.innerHTML = html;
}

// =============================================
// PAGINACIÓN
// =============================================
function mostrarPaginacion(totalPages, totalItems) {
    const wrap = document.getElementById('paginacionWrap');
    if (totalItems === 0) { wrap.innerHTML = ''; return; }

    const inicio = (currentPage - 1) * rowsPerPage + 1;
    const fin    = Math.min(currentPage * rowsPerPage, totalItems);

    let html = `
        <div class="paginacion-info">
            Mostrando ${inicio}–${fin} de ${totalItems} usuario${totalItems !== 1 ? 's' : ''}
        </div>
        <div class="paginacion">
    `;

    html += `<button class="page-btn" onclick="cambiarPagina(${currentPage - 1})"
              ${currentPage === 1 ? 'disabled' : ''}>
               <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M15 18l-6-6 6-6"/></svg>
             </button>`;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || Math.abs(i - currentPage) <= 2) {
            html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="cambiarPagina(${i})">${i}</button>`;
        } else if (Math.abs(i - currentPage) === 3) {
            html += `<button class="page-btn" disabled>…</button>`;
        }
    }

    html += `<button class="page-btn" onclick="cambiarPagina(${currentPage + 1})"
              ${currentPage === totalPages ? 'disabled' : ''}>
               <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
             </button>`;

    html += '</div>';
    wrap.innerHTML = html;
}

function cambiarPagina(page) {
    const totalPages = Math.ceil(todosLosUsuarios.length / rowsPerPage);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        aplicarFiltrosYMostrar();
    }
}

// =============================================
// VER DETALLE
// =============================================
async function verUsuario(id, rol) {
    try {
        const res = await fetch(`/api/usuarios/${id}?rol=${rol}`);
        if (!res.ok) throw new Error('No encontrado');
        const u = await res.json();

        const nombre  = `${u.nombre} ${u.apellido_paterno || ''} ${u.apellido_materno || ''}`.trim();
        const inicial = nombre.charAt(0).toUpperCase();
        const rolLabel = rol === 'admin' ? 'Administrador' : 'Alumno';

        let extra = '';
        if (rol === 'alumno') {
            extra = `
                <div class="detail-item">
                    <label>Matrícula</label>
                    <div class="val">${u.matricula || '—'}</div>
                </div>
                <div class="detail-item">
                    <label>Carrera</label>
                    <div class="val">${u.nombre_carrera || '—'}</div>
                </div>
                <div class="detail-item">
                    <label>Primer inicio de sesión</label>
                    <div class="val">${u.primer_login ? 'Pendiente' : 'Completado'}</div>
                </div>`;
        } else {
            extra = `
                <div class="detail-item">
                    <label>N° Control</label>
                    <div class="val">${u.matricula || '—'}</div>
                </div>`;
        }

        document.getElementById('modalVerBody').innerHTML = `
            <div class="detail-avatar">${inicial}</div>
            <div class="detail-grid">
                <div class="detail-item">
                    <label>Nombre completo</label>
                    <div class="val">${nombre}</div>
                </div>
                <div class="detail-item">
                    <label>Correo electrónico</label>
                    <div class="val">${u.correo || '—'}</div>
                </div>
                <div class="detail-item">
                    <label>Rol</label>
                    <div class="val">${rolLabel}</div>
                </div>
                ${extra}
            </div>`;

        abrirModal('modalVerUsuario');
    } catch (err) {
        Swal.fire('Error', 'No se pudo obtener el detalle del usuario.', 'error');
    }
}

// =============================================
// NUEVO USUARIO
// =============================================
function abrirModalNuevo() {
    document.getElementById('formUsuario').reset();
    document.getElementById('formUserId').value     = '';
    document.getElementById('formModoEdicion').value = '0';
    document.getElementById('modalFormTitulo').innerHTML =
        '<i class="fas fa-user-plus"></i> Nuevo usuario';
    document.getElementById('grupoRol').style.display = '';
    document.getElementById('camposAlumno').style.display = '';
    document.getElementById('camposAdmin').style.display  = 'none';
    // Resetear radio al primer valor
    document.querySelector('input[name="rol"][value="alumno"]').checked = true;
    abrirModal('modalFormUsuario');
}

// =============================================
// EDITAR USUARIO
// =============================================
async function editarUsuario(id, rol) {
    try {
        const res = await fetch(`/api/usuarios/${id}?rol=${rol}`);
        if (!res.ok) throw new Error('No encontrado');
        const u = await res.json();

        document.getElementById('formUserId').value      = id;
        document.getElementById('formModoEdicion').value = '1';
        document.getElementById('modalFormTitulo').innerHTML =
            '<i class="fas fa-user-edit"></i> Editar usuario';

        // Ocultar selector de rol en edición
        document.getElementById('grupoRol').style.display = 'none';
        // Mantener el radio con el rol correcto (para que el submit sepa el tipo)
        const radioRol = document.querySelector(`input[name="rol"][value="${rol === 'admin' ? 'admin' : 'alumno'}"]`);
        if (radioRol) radioRol.checked = true;

        // Rellenar campos
        document.getElementById('inputNombre').value    = u.nombre      || '';
        document.getElementById('inputApellidoP').value = u.apellido_paterno || '';
        document.getElementById('inputApellidoM').value = u.apellido_materno || '';
        document.getElementById('inputCorreo').value    = u.correo      || '';

        if (rol === 'alumno') {
            document.getElementById('inputMatricula').value = u.matricula || '';
            document.getElementById('inputCarrera').value   = u.id_carrera || '';
            document.getElementById('camposAlumno').style.display = '';
            document.getElementById('camposAdmin').style.display  = 'none';
        } else {
            document.getElementById('camposAlumno').style.display = 'none';
            document.getElementById('camposAdmin').style.display  = '';
            // En edición de admin no pedimos nueva contraseña
            document.getElementById('hintAdmin').style.display = 'none';
        }

        abrirModal('modalFormUsuario');
    } catch (err) {
        Swal.fire('Error', 'No se pudo cargar el usuario para editar.', 'error');
    }
}

// =============================================
// GUARDAR (crear / actualizar)
// =============================================
async function guardarUsuario(e) {
    e.preventDefault();

    const id        = document.getElementById('formUserId').value;
    const esEdicion = document.getElementById('formModoEdicion').value === '1';
    const rol       = document.querySelector('input[name="rol"]:checked')?.value || 'alumno';

    const nombre    = document.getElementById('inputNombre').value.trim();
    const apellidoP = document.getElementById('inputApellidoP').value.trim();
    const apellidoM = document.getElementById('inputApellidoM').value.trim();
    const correo    = document.getElementById('inputCorreo').value.trim();

    // ── Validaciones ─────────────────────────
    const soloLetras = /^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]+$/;

    if (!nombre || !apellidoP || !correo) {
        return Swal.fire('Campos incompletos', 'Nombre, apellido paterno y correo son obligatorios.', 'warning');
    }
    if (!soloLetras.test(nombre)) {
        return Swal.fire('Dato inválido', 'El nombre solo puede contener letras.', 'warning');
    }
    if (!soloLetras.test(apellidoP)) {
        return Swal.fire('Dato inválido', 'El apellido paterno solo puede contener letras.', 'warning');
    }
    if (apellidoM && !soloLetras.test(apellidoM)) {
        return Swal.fire('Dato inválido', 'El apellido materno solo puede contener letras.', 'warning');
    }

    const payload = { nombre, apellido_paterno: apellidoP, apellido_materno: apellidoM, correo, rol };

    if (rol === 'alumno') {
        const matricula  = document.getElementById('inputMatricula').value.trim();
        const id_carrera = document.getElementById('inputCarrera').value;
        if (!matricula) {
            return Swal.fire('Campos incompletos', 'La matrícula es obligatoria para alumnos.', 'warning');
        }
        payload.matricula  = matricula;
        payload.id_carrera = id_carrera || null;
    }

    // ── Envío ─────────────────────────────────
    const url    = esEdicion ? `/api/usuarios/${id}` : '/api/usuarios';
    const method = esEdicion ? 'PUT' : 'POST';

    const btn = document.getElementById('btnGuardarUsuario');
    btn.disabled = true;
    document.getElementById('btnGuardarTexto').textContent = 'Guardando…';

    try {
        const res  = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            cerrarModalForm();
            await Swal.fire({
                icon: 'success',
                title: esEdicion ? '¡Actualizado!' : '¡Registrado!',
                text: data.message,
                timer: 2000,
                showConfirmButton: false
            });
            cargarUsuarios();
        } else {
            Swal.fire('Error', data.message || 'No se pudo guardar el usuario.', 'error');
        }
    } catch (err) {
        console.error('Error al guardar:', err);
        Swal.fire('Error', 'Error de conexión al guardar el usuario.', 'error');
    } finally {
        btn.disabled = false;
        document.getElementById('btnGuardarTexto').textContent = 'Guardar';
    }
}

// =============================================
// ELIMINAR
// =============================================
async function eliminarUsuario(id, rol, nombre) {
    const result = await Swal.fire({
        title: `¿Eliminar a ${nombre}?`,
        text: 'Esta acción no se puede deshacer.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#c0392b',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar'
    });

    if (!result.isConfirmed) return;

    try {
        const res  = await fetch(`/api/usuarios/${id}?rol=${rol}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            await Swal.fire({ icon: 'success', title: 'Eliminado', timer: 1600, showConfirmButton: false });
            cargarUsuarios();
        } else {
            Swal.fire('Error', data.message || 'No se pudo eliminar.', 'error');
        }
    } catch (err) {
        Swal.fire('Error', 'Error al eliminar el usuario.', 'error');
    }
}

// =============================================
// HELPERS DE MODAL
// =============================================
function abrirModal(id)  { document.getElementById(id).classList.add('open');    }
function cerrarModalVer() { document.getElementById('modalVerUsuario').classList.remove('open'); }
function cerrarModalForm() { document.getElementById('modalFormUsuario').classList.remove('open'); }

function onCambioRol(rol) {
    document.getElementById('camposAlumno').style.display = rol === 'alumno' ? '' : 'none';
    document.getElementById('camposAdmin').style.display  = rol === 'admin'  ? '' : 'none';
    if (rol === 'admin') {
        document.getElementById('hintAdmin').style.display = '';
    }
}