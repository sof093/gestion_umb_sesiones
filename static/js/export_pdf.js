// Módulo para exportación de PDF personalizada
class PDFExporter {
    constructor() {
        this.eventoId = null;
        this.selectedLogos = [];
        this.tempUploads = {
            izquierda: null,
            centro: null,
            derecha: null
        };
        this.init();
    }
    
    init() {
        console.log('✅ PDFExporter inicializado');
        this.bindEvents();
    }
    
    bindEvents() {
        // Botón de exportar PDF en la interfaz
        const btnExportPdf = document.getElementById('btnExportPdf');
        if (btnExportPdf) {
            console.log('✅ Botón Exportar PDF encontrado');
            btnExportPdf.addEventListener('click', () => this.openModal());
        } else {
            console.error('❌ Botón btnExportPdf NO encontrado');
        }
        
        // Cerrar modal
        const closeBtn = document.getElementById('modalExportClose');
        const cancelBtn = document.getElementById('btnExportCancel');
        if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.closeModal());
        
        // Generar PDF
        const generateBtn = document.getElementById('btnGeneratePdf');
        if (generateBtn) {
            console.log('✅ Botón Generar PDF encontrado');
            generateBtn.addEventListener('click', () => this.generatePDF());
        } else {
            console.error('❌ Botón btnGeneratePdf NO encontrado');
        }
        
        // Seleccionar todos
        const selectAll = document.getElementById('selectAllLogos');
        if (selectAll) {
            selectAll.addEventListener('change', (e) => this.selectAllLogos(e.target.checked));
        }
        
        // Upload de logos
        document.querySelectorAll('.logo-upload-input').forEach(input => {
            input.addEventListener('change', (e) => this.handleLogoUpload(e.target));
        });
        
        // Limpiar logos
        document.querySelectorAll('.btn-clear-logo').forEach(btn => {
            btn.addEventListener('click', (e) => this.clearLogo(btn.dataset.position));
        });
        
        // Cerrar con ESC
        document.addEventListener('keydown', (e) => {
            const modal = document.getElementById('modalExportPdf');
            if (e.key === 'Escape' && modal && modal.style.display !== 'none') {
                this.closeModal();
            }
        });
    }
    
    async openModal() {
        console.log('📂 Abriendo modal de exportación...');
        
        // Obtener evento activo
        const eventoSelect = document.getElementById('eventoSelect');
        if (!eventoSelect || !eventoSelect.value) {
            Swal.fire('Error', 'No hay una jornada activa seleccionada', 'error');
            return;
        }
        
        this.eventoId = eventoSelect.value;
        document.getElementById('exportEventoId').value = this.eventoId;
        console.log(`📅 Evento ID: ${this.eventoId}`);
        
        // Mostrar modal ANTES de cargar datos para que el usuario vea algo
        const modal = document.getElementById('modalExportPdf');
        modal.style.display = 'flex';
        
        // Resetear formulario
        this.resetForm();
        
        // Cargar instituciones del evento
        await this.loadInstituciones();
    }
    
    closeModal() {
        console.log('🔒 Cerrando modal');
        const modal = document.getElementById('modalExportPdf');
        if (modal) modal.style.display = 'none';
    }
    
    async loadInstituciones() {
        const container = document.getElementById('institucionesLogosList');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Cargando instituciones...</div>';
        
        try {
            console.log(`🌐 Fetching: /admin/eventos/${this.eventoId}/instituciones-logos`);
            const response = await fetch(`/admin/eventos/${this.eventoId}/instituciones-logos`);
            const data = await response.json();
            
            console.log('📊 Datos recibidos:', data);
            
            if (data.success && data.instituciones && data.instituciones.length > 0) {
                console.log(`🏢 Renderizando ${data.instituciones.length} instituciones`);
                this.renderInstitucionesList(data.instituciones);
                const selectAll = document.getElementById('selectAllLogos');
                if (selectAll) selectAll.checked = true;
                this.updateLogosCount();
            } else {
                container.innerHTML = '<div class="loading-spinner"><i class="fas fa-info-circle"></i> No hay logos de instituciones disponibles para esta jornada</div>';
            }
        } catch (error) {
            console.error('❌ Error cargando instituciones:', error);
            container.innerHTML = '<div class="loading-spinner"><i class="fas fa-exclamation-triangle"></i> Error al cargar instituciones. Verifica la conexión.</div>';
        }
    }
    
    renderInstitucionesList(instituciones) {
    const container = document.getElementById('institucionesLogosList');
    if (!container) return;
    
    container.innerHTML = '';
    
    instituciones.forEach((inst, index) => {
        const div = document.createElement('div');
        div.className = 'institucion-logo-item';
        
        // Construir ruta correcta de la imagen
        let imgSrc = inst.logo_path || '';
        
        // Intentar diferentes rutas posibles
        const possiblePaths = [
            imgSrc,
            '/' + imgSrc,
            '/static/' + imgSrc,
            '/static/uploads/sesiones/' + imgSrc.split('/').pop(),
            '/static/img/' + imgSrc.split('/').pop()
        ];
        
        // Usar la primera ruta como intento
        const finalSrc = possiblePaths[0];
        
        div.innerHTML = `
            <input type="checkbox" class="logo-checkbox" data-id="${inst.id}" value="${inst.logo_path}" checked>
            <div class="logo-thumb-container">
                <img src="${finalSrc}" class="logo-thumb" 
                     onerror="this.onerror=null; this.style.display='none'; this.parentElement.querySelector('.logo-placeholder').style.display='flex';">
                <div class="logo-placeholder" style="display: none; width: 50px; height: 50px; background: #f0f0f0; border-radius: 8px; align-items: center; justify-content: center; font-size: 20px; color: #999;">
                    🏛️
                </div>
            </div>
            <span class="institucion-nombre">${this.escapeHtml(inst.nombre)}</span>
        `;
        container.appendChild(div);
    });
    
    // Agregar event listeners a checkboxes
    document.querySelectorAll('.logo-checkbox').forEach(cb => {
        cb.addEventListener('change', () => this.updateLogosCount());
    });
}
    updateLogosCount() {
        const checkboxes = document.querySelectorAll('.logo-checkbox');
        const selected = Array.from(checkboxes).filter(cb => cb.checked).length;
        const total = checkboxes.length;
        const countSpan = document.getElementById('logosCount');
        if (countSpan) {
            countSpan.innerText = `${selected} de ${total} logos seleccionados`;
        }
        
        // Actualizar "seleccionar todos"
        const selectAll = document.getElementById('selectAllLogos');
        if (selectAll && total > 0) {
            selectAll.checked = selected === total;
            selectAll.indeterminate = selected > 0 && selected < total;
        }
    }
    
    selectAllLogos(checked) {
        document.querySelectorAll('.logo-checkbox').forEach(cb => {
            cb.checked = checked;
        });
        this.updateLogosCount();
    }
    
    async handleLogoUpload(input) {
        const position = input.dataset.position;
        const file = input.files[0];
        
        if (!file) return;
        
        console.log(`📤 Subiendo logo ${position}: ${file.name}`);
        
        // Validar tipo y tamaño
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            Swal.fire('Error', 'Formato no válido. Use PNG, JPG o WEBP', 'error');
            input.value = '';
            return;
        }
        
        if (file.size > 2 * 1024 * 1024) {
            Swal.fire('Error', 'El archivo no debe superar los 2MB', 'error');
            input.value = '';
            return;
        }
        
        // Mostrar preview
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewDiv = document.getElementById(`preview${this.capitalize(position)}`);
            if (previewDiv) {
                previewDiv.innerHTML = `<img src="${e.target.result}" alt="Preview ${position}" style="max-width:100%; max-height:100%; object-fit:contain;">`;
                console.log(`✅ Preview actualizado para ${position}`);
            }
            this.tempUploads[position] = file;
        };
        reader.onerror = (err) => {
            console.error(`❌ Error leyendo archivo ${position}:`, err);
            Swal.fire('Error', 'No se pudo leer el archivo', 'error');
        };
        reader.readAsDataURL(file);
    }
    
    clearLogo(position) {
        console.log(`🗑️ Limpiando logo ${position}`);
        const previewDiv = document.getElementById(`preview${this.capitalize(position)}`);
        if (previewDiv) {
            previewDiv.innerHTML = '<i class="fas fa-image"></i><span>Sin logo</span>';
        }
        
        const input = document.querySelector(`.logo-upload-input[data-position="${position}"]`);
        if (input) input.value = '';
        
        this.tempUploads[position] = null;
    }
    
    async generatePDF() {
        const generateBtn = document.getElementById('btnGeneratePdf');
        if (!generateBtn) {
            console.error('❌ Botón Generar PDF no encontrado');
            Swal.fire('Error', 'Error interno: botón no encontrado', 'error');
            return;
        }
        
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
        generateBtn.disabled = true;
        
        try {
            // Obtener logos seleccionados del pie
            const selectedLogos = Array.from(document.querySelectorAll('.logo-checkbox:checked'))
                .map(cb => cb.value)
                .filter(v => v); // Filtrar vacíos
            
            console.log(`📋 Logos seleccionados para el pie: ${selectedLogos.length}`);
            
            // Crear FormData para enviar archivos
            const formData = new FormData();
            formData.append('evento_id', this.eventoId);
            formData.append('logos_pie', JSON.stringify(selectedLogos));
            
            // Agregar logos del encabezado si se subieron nuevos
            let hasCustomLogos = false;
            for (const [position, file] of Object.entries(this.tempUploads)) {
                if (file) {
                    console.log(`📎 Adjuntando logo_${position}: ${file.name}`);
                    formData.append(`logo_${position}`, file);
                    hasCustomLogos = true;
                }
            }
            
            if (!hasCustomLogos) {
                console.log('ℹ️ No se subieron logos personalizados, se usarán los default');
            }
            
            console.log('🚀 Enviando petición al servidor...');
            const response = await fetch('/admin/eventos/exportar-pdf-personalizado', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // Descargar archivo
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `itinerario_personalizado_${this.eventoId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                
                console.log('✅ PDF generado y descargado correctamente');
                Swal.fire('Éxito', 'PDF generado correctamente', 'success');
                this.closeModal();
            } else {
                let errorMsg = 'Error al generar PDF';
                try {
                    const error = await response.json();
                    errorMsg = error.message || errorMsg;
                } catch(e) {}
                throw new Error(errorMsg);
            }
        } catch (error) {
            console.error('❌ Error en generatePDF:', error);
            Swal.fire('Error', error.message || 'Error al generar el PDF', 'error');
        } finally {
            if (generateBtn) {
                generateBtn.innerHTML = originalText;
                generateBtn.disabled = false;
            }
        }
    }
    
    resetForm() {
        console.log('🔄 Resetear formulario');
        // Limpiar previews
        ['izquierda', 'centro', 'derecha'].forEach(pos => {
            this.clearLogo(pos);
        });
        
        // Resetear selección de logos
        this.selectAllLogos(true);
        
        // Limpiar tempUploads
        this.tempUploads = { izquierda: null, centro: null, derecha: null };
    }
    
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM cargado, inicializando PDFExporter...');
    window.pdfExporter = new PDFExporter();
});