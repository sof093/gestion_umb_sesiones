
    // Variables globales
    let todasLasSesiones = [];
    let currentPage = 1;
    let rowsPerPage = 10;
    let currentSearch = '';
    let currentFilterTipo = '';
    let currentFilterEscenario = '';
    // Función para cargar sesiones
    async function cargarSesiones() {
        console.log("Cargando sesiones...");
        
        try {
            const response = await fetch('/api/sesiones');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            todasLasSesiones = await response.json();
            console.log("Sesiones recibidas:", todasLasSesiones.length);
            
            aplicarFiltrosYMostrar();
            
        } catch (error) {
            console.error("Error al cargar sesiones:", error);
            const tbody = document.getElementById('tablaCuerpo');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: red;">Error al cargar las sesiones</td></tr>';
            }
        }
    }

    // Aplicar filtros y mostrar
    function aplicarFiltrosYMostrar() {
        let datosFiltrados = [...todasLasSesiones];
        
        // Aplicar búsqueda
        if (currentSearch) {
            const searchLower = currentSearch.toLowerCase();
            datosFiltrados = datosFiltrados.filter(sesion => {
                const nombreCompleto = `${sesion.nombre_ponente || ''} ${sesion.apellido_paterno || ''} ${sesion.apellido_materno || ''}`.toLowerCase();
                return nombreCompleto.includes(searchLower) ||
                       (sesion.tipo && sesion.tipo.toLowerCase().includes(searchLower)) ||
                       (sesion.escenario_nombre && sesion.escenario_nombre.toLowerCase().includes(searchLower));
            });
        }
        
        // Aplicar filtro por tipo
        // Aplicar filtro por tipo
        if (currentFilterTipo) {
            datosFiltrados = datosFiltrados.filter(sesion => sesion.tipo === currentFilterTipo);
        }

        // Aplicar filtro por escenario
        if (currentFilterEscenario) {
            datosFiltrados = datosFiltrados.filter(sesion => sesion.escenario_nombre === currentFilterEscenario);
        }
        
        // Calcular paginación
        const totalPages = Math.ceil(datosFiltrados.length / rowsPerPage);
        const start = (currentPage - 1) * rowsPerPage;
        const end = start + rowsPerPage;
        const datosPagina = datosFiltrados.slice(start, end);
        
        // Mostrar tabla y paginación
        mostrarTabla(datosPagina);
        mostrarPaginacion(totalPages, datosFiltrados.length);
    }

    // Mostrar tabla
    function mostrarTabla(sesiones) {
        const tbody = document.getElementById('tablaCuerpo');
        if (!tbody) return;
        
        if (sesiones.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No hay sesiones que coincidan con los criterios</td></tr>';
            return;
        }
        
        let html = '';
        for (const sesion of sesiones) {
            const nombreCompleto = `${sesion.nombre_ponente || ''} ${sesion.apellido_paterno || ''} ${sesion.apellido_materno || ''}`.trim();
            const fecha = sesion.fecha_str || (sesion.fecha ? new Date(sesion.fecha).toLocaleDateString() : 'N/A');
            const horaInicio = sesion.hora_inicio_str || sesion.hora_inicio || 'N/A';
            const horaFin = sesion.hora_fin_str || sesion.hora_fin || 'N/A';
            
            let badgeClass = 'badge-inauguracion';
            if (sesion.tipo === 'Conferencia magistral') badgeClass = 'badge-conferencia-magistral';
            else if (sesion.tipo === 'Conferencia') badgeClass = 'badge-conferencia';
            else if (sesion.tipo === 'Taller') badgeClass = 'badge-taller';
            else if (sesion.tipo === 'Exhibición') badgeClass = 'badge-exhibicion';
            else if (sesion.tipo === 'Cierre del evento') badgeClass = 'badge-cierre';
            
            html += `
                <tr>
                    <td class="sesion-info">
                        <div class="sesion-nombre"><strong>${sesion.nombre_de_sesion || 'Sin nombre'}</strong></div>
                        <div class="sesion-fecha">${fecha}</div>
                        <div class="sesion-horario">${horaInicio} - ${horaFin}</div>
                        <div class="sesion-cupo">Cupo: ${sesion.cupo_audiencia || 'N/A'}</div>
                        <div class="sesion-sede">${sesion.sede || 'N/A'}</div>
                    </td>
                    <td class="ponente-info">
                        <div class="ponente-nombre">${nombreCompleto}</div>
                        ${sesion.perfil_profesional ? `<div class="ponente-perfil">${sesion.perfil_profesional.substring(0, 100)}${sesion.perfil_profesional.length > 100 ? '...' : ''}</div>` : ''}
                    </td>
                    <td><span class="${badgeClass}">${sesion.tipo || 'N/A'}</span></td>
                    <td>${sesion.escenario_nombre || 'N/A'}</td>
                    <td class="acciones">
                        <a href="/admin/sesion/editar/${sesion.id_sesion}" class="btn-icon-action edit" title="Editar">Editar</a>
                        <button onclick="eliminarSesion(${sesion.id_sesion})" class="btn-icon-action delete" title="Eliminar">Eliminar</button>
                    </td>
                </tr>
            `;
        }
        
        tbody.innerHTML = html;
    }

    // Mostrar paginación
    function mostrarPaginacion(totalPages, totalItems) {
        const wrap = document.getElementById('paginacionWrap');
        if (!wrap) return;
        
        if (totalPages <= 1) {
            wrap.innerHTML = '';
            return;
        }
        
        let html = `<div style="padding: 1rem; text-align: center; color: #666; font-size: 0.85rem;">Mostrando ${((currentPage-1)*rowsPerPage)+1} a ${Math.min(currentPage*rowsPerPage, totalItems)} de ${totalItems} sesiones</div>`;
        html += '<div class="paginacion">';
        
        // Botón anterior
        html += `<button class="page-btn" onclick="cambiarPagina(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>«</button>`;
        
        // Números de página
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="cambiarPagina(${i})">${i}</button>`;
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                html += `<button class="page-btn" disabled>...</button>`;
            }
        }
        
        // Botón siguiente
        html += `<button class="page-btn" onclick="cambiarPagina(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>»</button>`;
        html += '</div>';
        
        wrap.innerHTML = html;
    }

    // Cambiar página
    function cambiarPagina(page) {
        const totalPages = Math.ceil(todasLasSesiones.filter(s => {
            if (currentSearch) {
                const nombreCompleto = `${s.nombre_ponente || ''} ${s.apellido_paterno || ''} ${s.apellido_materno || ''}`.toLowerCase();
                return nombreCompleto.includes(currentSearch.toLowerCase()) ||
                       (s.tipo && s.tipo.toLowerCase().includes(currentSearch.toLowerCase())) ||
                       (s.escenario_nombre && s.escenario_nombre.toLowerCase().includes(currentSearch.toLowerCase()));
            }
            return true;
        }).filter(s => currentFilterTipo ? s.tipo === currentFilterTipo : true)
         .filter(s => currentFilterEscenario ? s.escenario_nombre === currentFilterEscenario : true).length / rowsPerPage);
        if (page >= 1 && page <= totalPages) {
            currentPage = page;
            aplicarFiltrosYMostrar();
        }
    }

    // Eliminar sesión
    async function eliminarSesion(id) {
        const result = await Swal.fire({
            title: '¿Eliminar sesión?',
            text: 'Esta acción no se puede deshacer',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        });
        
        if (result.isConfirmed) {
            try {
                const response = await fetch(`/admin/sesion/eliminar/${id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.success) {
                    Swal.fire('Eliminado', 'La sesión ha sido eliminada', 'success');
                    cargarSesiones();
                } else {
                    Swal.fire('Error', data.message || 'No se pudo eliminar', 'error');
                }
            } catch (error) {
                console.error("Error al eliminar:", error);
                Swal.fire('Error', 'Error al eliminar la sesión', 'error');
            }
        }
    }

    // Event listeners
    document.addEventListener('DOMContentLoaded', function() {
        cargarSesiones();
        
        // Búsqueda en tiempo real
        const buscarInput = document.getElementById('buscarInput');
        if (buscarInput) {
            buscarInput.addEventListener('input', function(e) {
                currentSearch = e.target.value;
                currentPage = 1;
                aplicarFiltrosYMostrar();
            });
        }
        
        // Filtro por tipo
        // Filtro por tipo
        const filtroTipoSelect = document.getElementById('selectFiltroTipo');
        if (filtroTipoSelect) {
            filtroTipoSelect.addEventListener('change', function(e) {
                currentFilterTipo = e.target.value;
                currentPage = 1;
                aplicarFiltrosYMostrar();
            });
        }

        // Filtro por escenario
        const filtroEscenarioSelect = document.getElementById('selectFiltroEscenario');
        if (filtroEscenarioSelect) {
            filtroEscenarioSelect.addEventListener('change', function(e) {
                currentFilterEscenario = e.target.value;
                currentPage = 1;
                aplicarFiltrosYMostrar();
            });
        }
        
        // Cambiar cantidad por página
        const selectMostrar = document.getElementById('selectMostrar');
        if (selectMostrar) {
            selectMostrar.addEventListener('change', function(e) {
                rowsPerPage = parseInt(e.target.value);
                currentPage = 1;
                aplicarFiltrosYMostrar();
            });
        }
    });