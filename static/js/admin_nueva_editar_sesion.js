// Variable para detectar cambios en el formulario
let formModified = false;
let formSubmitted = false;

// ============================================
// DEFINIR LÍMITES POR ESCENARIO (AL PRINCIPIO)
// ============================================
const limitesPorEscenario = {
    1: 100,  // Aula magna
    3: 25,// Aula A
    2: 20,// 2: 80,   // Laboratorio de cómputo (sin límite, no lo incluyas)
    // 4: 200,  // Plazoleta institucional (sin límite)
    // 5: 500   // Áreas verdes (sin límite)
};

// ============================================
// NUEVAS FUNCIONES PARA VERIFICAR DISPONIBILIDAD
// ============================================

// Variable para evitar múltiples verificaciones
let verificandoDisponibilidad = false;
let timeoutVerificacion = null;

// Función para mostrar mensaje de disponibilidad
function mostrarMensajeDisponibilidad(tipo, mensaje) {
    // Eliminar mensaje anterior si existe
    eliminarMensajeDisponibilidad();
    
    // Crear contenedor de mensaje si no existe
    let mensajeDiv = document.getElementById('mensaje-disponibilidad');
    if (!mensajeDiv) {
        mensajeDiv = document.createElement('div');
        mensajeDiv.id = 'mensaje-disponibilidad';
        mensajeDiv.style.marginTop = '10px';
        mensajeDiv.style.padding = '10px';
        mensajeDiv.style.borderRadius = '5px';
        mensajeDiv.style.fontSize = '14px';
        
        // Insertar después del campo escenario
        const escenarioField = document.getElementById('id_escenario').closest('.form-group');
        if (escenarioField && escenarioField.parentNode) {
            escenarioField.parentNode.insertBefore(mensajeDiv, escenarioField.nextSibling);
        }
    }
    
    mensajeDiv.style.display = 'block';
    
    if (tipo === 'success') {
        mensajeDiv.style.backgroundColor = '#d4edda';
        mensajeDiv.style.color = '#155724';
        mensajeDiv.style.border = '1px solid #c3e6cb';
    } else {
        mensajeDiv.style.backgroundColor = '#f8d7da';
        mensajeDiv.style.color = '#721c24';
        mensajeDiv.style.border = '1px solid #f5c6cb';
    }
    
    mensajeDiv.innerHTML = mensaje;
    
    // Si es error, también marcar los campos
    if (tipo === 'error') {
        const escenarioField = document.getElementById('id_escenario');
        const horaInicioField = document.getElementById('hora_inicio');
        const horaFinField = document.getElementById('hora_fin');
        
        if (escenarioField) escenarioField.style.borderColor = '#dc3545';
        if (horaInicioField) horaInicioField.style.borderColor = '#dc3545';
        if (horaFinField) horaFinField.style.borderColor = '#dc3545';
    } else {
        const escenarioField = document.getElementById('id_escenario');
        const horaInicioField = document.getElementById('hora_inicio');
        const horaFinField = document.getElementById('hora_fin');
        
        if (escenarioField) escenarioField.style.borderColor = '';
        if (horaInicioField) horaInicioField.style.borderColor = '';
        if (horaFinField) horaFinField.style.borderColor = '';
    }
}

// Función para eliminar mensaje de disponibilidad
function eliminarMensajeDisponibilidad() {
    const mensajeDiv = document.getElementById('mensaje-disponibilidad');
    if (mensajeDiv) {
        mensajeDiv.style.display = 'none';
    }
}

// Función para verificar disponibilidad del escenario
async function verificarDisponibilidadEscenario() {
    // Evitar verificar si ya hay una verificación en curso
    if (verificandoDisponibilidad) return;
    
    const idEscenario = document.getElementById('id_escenario').value;
    const fecha = document.getElementById('fecha').value;
    const horaInicio = document.getElementById('hora_inicio').value;
    const horaFin = document.getElementById('hora_fin').value;
    const esEdicion = window.location.pathname.includes('/editar/');
    
    // Solo verificar si todos los campos están llenos
    if (!idEscenario || !fecha || !horaInicio || !horaFin) {
        eliminarMensajeDisponibilidad();
        return;
    }
    
    // Validar que hora_fin > hora_inicio
    if (horaAMinutos(horaInicio) >= horaAMinutos(horaFin)) {
        mostrarMensajeDisponibilidad('error', 'La hora de fin debe ser posterior a la hora de inicio');
        return;
    }
    
    verificandoDisponibilidad = true;
    
    try {
        let url = '/admin/verificar_disponibilidad';
        let idSesion = null;
        
        if (esEdicion) {
            idSesion = window.location.pathname.split('/').pop();
        }
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_escenario: idEscenario,
                fecha: fecha,
                hora_inicio: horaInicio,
                hora_fin: horaFin,
                id_sesion: idSesion
            })
        });
        
        const data = await response.json();
        
        if (data.disponible) {
            mostrarMensajeDisponibilidad('success', '✓ Escenario disponible para este horario');
        } else {
            mostrarMensajeDisponibilidad('error', data.mensaje);
        }
    } catch (error) {
        console.error('Error al verificar disponibilidad:', error);
        mostrarMensajeDisponibilidad('error', 'Error al verificar disponibilidad');
    } finally {
        verificandoDisponibilidad = false;
    }
}

// Función para verificar disponibilidad con debounce
function verificarConDebounce() {
    if (timeoutVerificacion) {
        clearTimeout(timeoutVerificacion);
    }
    timeoutVerificacion = setTimeout(() => {
        verificarDisponibilidadEscenario();
    }, 500);
}

// ============================================
// FUNCIONES BASE
// ============================================

// Función para convertir hora HH:MM a minutos
function horaAMinutos(horaStr) {
    if (!horaStr) return 0;
    const partes = horaStr.split(':');
    if (partes.length === 2) {
        return parseInt(partes[0]) * 60 + parseInt(partes[1]);
    }
    return 0;
}

// Función para validar solo letras y espacios
function soloLetras(texto) {
    return /^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]*$/.test(texto);
}

// Función para validar número positivo
function esNumeroPositivo(valor) {
    if (!valor) return true;
    const num = parseInt(valor);
    return !isNaN(num) && num > 0;
}

// Función para validar archivo de imagen
function esImagenValida(file) {
    if (!file || !file.name) return true;
    const extensiones = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
    const extension = file.name.split('.').pop().toLowerCase();
    return extensiones.includes(extension);
}

// Función para mostrar errores
function mostrarError(campoId, mensaje) {
    const errorDiv = document.getElementById(`error-${campoId}`);
    if (errorDiv) {
        errorDiv.textContent = mensaje;
        errorDiv.style.display = 'block';
    }
    const campo = document.getElementById(campoId);
    if (campo) {
        campo.style.borderColor = '#dc3545';
    }
}

// Función para limpiar errores
function limpiarErrores() {
    document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');
    document.querySelectorAll('input, select, textarea').forEach(el => {
        el.style.borderColor = '';
    });
}

// Validar fecha no pasada
function fechaNoPasada(fechaStr) {
    if (!fechaStr) return true;
    const fechaSeleccionada = new Date(fechaStr);
    const fechaActual = new Date();
    fechaActual.setHours(0, 0, 0, 0);
    return fechaSeleccionada >= fechaActual;
}

// Función para validar horas en tiempo real
function validarHorasEnTiempoReal() {
    const horaInicio = document.getElementById('hora_inicio');
    const horaFin = document.getElementById('hora_fin');
    
    if (horaInicio && horaFin && horaInicio.value && horaFin.value) {
        const minutosInicio = horaAMinutos(horaInicio.value);
        const minutosFin = horaAMinutos(horaFin.value);
        
        if (minutosInicio >= minutosFin) {
            mostrarError('hora_fin', 'La hora de fin debe ser posterior a la hora de inicio');
            return false;
        } else {
            const errorDiv = document.getElementById('error-hora_fin');
            if (errorDiv) errorDiv.style.display = 'none';
            horaFin.style.borderColor = '';
            return true;
        }
    }
    return true;
}

// ============================================
// FUNCIÓN PARA LIMITAR CUPO SEGÚN ESCENARIO
// ============================================
function actualizarLimiteCupoPorEscenario() {
    const escenarioSelect = document.getElementById('id_escenario');
    const cupoInput = document.getElementById('cupo_audiencia');
    
    if (!escenarioSelect || !cupoInput) return;
    
    const escenarioId = escenarioSelect.value;
    const limite = limitesPorEscenario[escenarioId];
    const nombreEscenario = escenarioSelect.options[escenarioSelect.selectedIndex]?.text;
    
    // 🔥 ELIMINAR EL ATRIBUTO MAX completamente
    cupoInput.removeAttribute('max');
    
    // Remover mensaje de ayuda anterior si existe
    const ayudaExistente = document.getElementById('ayuda-limite-cupo');
    if (ayudaExistente) ayudaExistente.remove();
    
    if (limite) {
        // 🔥 NO USAR cupoInput.max = limite
        // Solo guardar el límite en un atributo personalizado
        cupoInput.setAttribute('data-limite', limite);
        cupoInput.placeholder = `Máximo ${limite} personas (${nombreEscenario})`;
        
        // Si el valor actual supera el límite, mostrar SweetAlert y ajustar
        let valorActual = parseInt(cupoInput.value);
        if (valorActual > limite) {
            cupoInput.value = limite;
            
            Swal.fire({
                title: 'Límite aplicado automáticamente',
                html: `<div style="text-align: left;">
                           <p><strong>📌 El escenario "${nombreEscenario}" tiene un límite de ${limite} personas.</strong></p>
                           <p>El cupo ha sido ajustado automáticamente a <strong>${limite}</strong> personas.</p>
                           <p>Puedes modificarlo, pero no podrá superar este límite.</p>
                       </div>`,
                icon: 'info',
                confirmButtonColor: '#2d6e3e',
                confirmButtonText: 'Entendido',
                timer: 3000,
                timerProgressBar: true
            });
        }
        
        // Limpiar cualquier error visual previo
        cupoInput.style.borderColor = '';
        const errorDiv = document.getElementById('error-cupo_audiencia');
        if (errorDiv) errorDiv.style.display = 'none';
        
        // Agregar mensaje de ayuda
        const ayuda = document.createElement('small');
        ayuda.id = 'ayuda-limite-cupo';
        ayuda.style.display = 'block';
        ayuda.style.color = '#2d6e3e';
        ayuda.style.marginTop = '5px';
        ayuda.style.fontSize = '12px';
        ayuda.innerHTML = `<i class="fas fa-info-circle"></i> Este escenario tiene un límite máximo de ${limite} personas`;
        cupoInput.parentNode.appendChild(ayuda);
        
    } else {
        // Sin límite
        cupoInput.removeAttribute('data-limite');
        cupoInput.placeholder = "Número de personas (sin límite específico)";
        cupoInput.style.borderColor = '';
        
        if (nombreEscenario && (nombreEscenario.includes('Plazoleta') || nombreEscenario.includes('Áreas'))) {
            const ayuda = document.createElement('small');
            ayuda.id = 'ayuda-limite-cupo';
            ayuda.style.display = 'block';
            ayuda.style.color = '#7a9a82';
            ayuda.style.marginTop = '5px';
            ayuda.style.fontSize = '12px';
            ayuda.innerHTML = `<i class="fas fa-info-circle"></i> Espacio abierto, capacidad flexible`;
            cupoInput.parentNode.appendChild(ayuda);
        }
    }
}
// Validación adicional en el formulario para el límite (VERSIÓN CON SWEETALERT)
function validarLimiteCupoEnvio() {
    const escenarioSelect = document.getElementById('id_escenario');
    const cupoInput = document.getElementById('cupo_audiencia');
    
    if (!escenarioSelect || !cupoInput) return true;
    
    // Usar el atributo personalizado en lugar de max
    const limite = parseInt(cupoInput.getAttribute('data-limite'));
    const valorCupo = parseInt(cupoInput.value);
    const nombreEscenario = escenarioSelect.options[escenarioSelect.selectedIndex]?.text;
    
    if (limite && !isNaN(valorCupo) && valorCupo > limite) {
        Swal.fire({
            title: '❌ Límite de cupo excedido',
            html: `<div style="text-align: left;">
                       <p><strong>No se puede guardar la sesión</strong></p>
                       <hr>
                       <p>📌 <strong>Escenario:</strong> ${nombreEscenario}</p>
                       <p>📌 <strong>Límite máximo:</strong> ${limite} personas</p>
                       <p>📌 <strong>Cupo ingresado:</strong> ${valorCupo} personas</p>
                       <hr>
                       <p>✏️ Por favor, ajusta el cupo a ${limite} o menos personas para continuar.</p>
                   </div>`,
            icon: 'error',
            confirmButtonColor: '#2d6e3e',
            confirmButtonText: 'Entendido, lo ajustaré'
        });
        
        // Marcar el campo como error visualmente
        cupoInput.style.borderColor = '#dc3545';
        const errorDiv = document.getElementById('error-cupo_audiencia');
        if (errorDiv) {
            errorDiv.textContent = `El cupo no puede exceder ${limite} personas`;
            errorDiv.style.display = 'block';
        }
        
        return false;
    }
    
    // Limpiar errores si está bien
    cupoInput.style.borderColor = '';
    const errorDiv = document.getElementById('error-cupo_audiencia');
    if (errorDiv) errorDiv.style.display = 'none';
    
    return true;
}
// ============================================
// VALIDACIÓN PRINCIPAL
// ============================================
function validarFormularioConLista() {
    let errores = [];
    
    limpiarErrores();
    
    // Validar fecha
    const fecha = document.getElementById('fecha');
    if (!fecha.value) {
        mostrarError('fecha', 'La fecha es requerida');
        errores.push('La fecha es requerida');
    } else if (!fechaNoPasada(fecha.value)) {
        mostrarError('fecha', 'La fecha no puede ser anterior al día de hoy');
        errores.push('La fecha no puede ser anterior al día de hoy');
    }
    
    // Validar sede
    const sede = document.getElementById('sede');
    if (!sede.value) {
        mostrarError('sede', 'La sede es requerida');
        errores.push('La sede es requerida');
    }
    
    // Validar nombre de sesión
    const nombreSesion = document.getElementById('nombre_de_sesion');
    if (!nombreSesion.value) {
        mostrarError('nombre_de_sesion', 'El nombre de la sesión es requerido');
        errores.push('El nombre de la sesión es requerido');
    }
    
    // Validar nombre ponente
    const nombre = document.getElementById('nombre_ponente');
    if (!nombre.value) {
        mostrarError('nombre_ponente', 'El nombre es requerido');
        errores.push('El nombre del ponente es requerido');
    } else if (!soloLetras(nombre.value)) {
        mostrarError('nombre_ponente', 'Solo se permiten letras y espacios');
        errores.push('El nombre solo puede contener letras y espacios');
    }
    
    // Validar apellido paterno
    const apPaterno = document.getElementById('apellido_paterno');
    if (!apPaterno.value) {
        mostrarError('apellido_paterno', 'El apellido paterno es requerido');
        errores.push('El apellido paterno es requerido');
    } else if (!soloLetras(apPaterno.value)) {
        mostrarError('apellido_paterno', 'Solo se permiten letras y espacios');
        errores.push('El apellido paterno solo puede contener letras y espacios');
    }
    
    // Validar apellido materno
    const apMaterno = document.getElementById('apellido_materno');
    if (apMaterno.value && !soloLetras(apMaterno.value)) {
        mostrarError('apellido_materno', 'Solo se permiten letras y espacios');
        errores.push('El apellido materno solo puede contener letras y espacios');
    }
    
    // Validar tipo de procedencia
    const tipoProcedencia = document.querySelector('input[name="tipo_procedencia"]:checked');
    if (!tipoProcedencia) {
        mostrarError('tipo_procedencia', 'Seleccione una opción');
        errores.push('Debe seleccionar si proviene de institución o es independiente');
    } else if (tipoProcedencia.value === 'institucion') {
        const nombreInstitucion = document.getElementById('nombre_institucion');
        if (!nombreInstitucion.value) {
            mostrarError('nombre_institucion', 'El nombre de la institución es requerido');
            errores.push('Debe ingresar el nombre de la institución');
        }
    }
    
    // Validar requiere materiales
    const requiereMateriales = document.querySelector('input[name="requiere_materiales"]:checked');
    if (!requiereMateriales) {
        mostrarError('requiere_materiales', 'Seleccione una opción');
        errores.push('Debe seleccionar si requiere materiales');
    } else if (requiereMateriales.value === 'si') {
        const descMateriales = document.getElementById('descripcion_materiales');
        if (!descMateriales.value.trim()) {
            mostrarError('descripcion_materiales', 'La descripción de materiales es requerida');
            errores.push('Debe describir los materiales necesarios');
        }
    }
    
    // Validación de horas
    const horaInicio = document.getElementById('hora_inicio');
    const horaFin = document.getElementById('hora_fin');
    
    if (!horaInicio.value) {
        mostrarError('hora_inicio', 'La hora de inicio es requerida');
        errores.push('La hora de inicio es requerida');
    }
    if (!horaFin.value) {
        mostrarError('hora_fin', 'La hora de fin es requerida');
        errores.push('La hora de fin es requerida');
    }
    if (horaInicio.value && horaFin.value) {
        const minutosInicio = horaAMinutos(horaInicio.value);
        const minutosFin = horaAMinutos(horaFin.value);
        
        if (minutosInicio >= minutosFin) {
            mostrarError('hora_fin', 'La hora de fin debe ser posterior a la hora de inicio');
            errores.push('La hora de fin debe ser después de la hora de inicio');
        }
    }
    
    // Validar tipo sesión
    const tipoSesion = document.getElementById('id_tipo_sesion');
    if (!tipoSesion.value) {
        mostrarError('id_tipo_sesion', 'Seleccione un tipo de sesión');
        errores.push('Debe seleccionar un tipo de sesión');
    }
    
    // Validar escenario
    const escenario = document.getElementById('id_escenario');
    if (!escenario.value) {
        mostrarError('id_escenario', 'Seleccione un escenario');
        errores.push('Debe seleccionar un escenario');
    }
    
    // Validar cupo (solo una vez)
    const cupo = document.getElementById('cupo_audiencia');
    if (cupo.value && !esNumeroPositivo(cupo.value)) {
        mostrarError('cupo_audiencia', 'Ingrese un número válido (mayor a 0)');
        errores.push('El cupo debe ser un número mayor a 0');
    }
    /*
    // Validar límite de cupo por escenario
    const escenarioId = document.getElementById('id_escenario').value;
    const limite = limitesPorEscenario[escenarioId];
    if (cupo.value && limite && parseInt(cupo.value) > limite) {
        const nombreEscenario = document.getElementById('id_escenario').options[document.getElementById('id_escenario').selectedIndex]?.text;
        mostrarError('cupo_audiencia', `El ${nombreEscenario} tiene un límite máximo de ${limite} personas`);
        errores.push(`El cupo no puede exceder ${limite} personas para este escenario`);
    }
    */
    // Validar fotografía
    const fotografia = document.getElementById('fotografia');
    if (fotografia.files.length > 0 && !esImagenValida(fotografia.files[0])) {
        mostrarError('fotografia', 'El archivo debe ser una imagen (JPG, PNG, GIF)');
        errores.push('La fotografía debe ser una imagen válida (JPG, PNG, GIF)');
    }
    
    // Validar logo
    const logo = document.getElementById('logo');
    if (logo.files.length > 0 && !esImagenValida(logo.files[0])) {
        mostrarError('logo', 'El archivo debe ser una imagen (JPG, PNG, GIF)');
        errores.push('El logo debe ser una imagen válida (JPG, PNG, GIF)');
    }
    
    // Verificar disponibilidad del escenario
    const mensajeDisponibilidad = document.getElementById('mensaje-disponibilidad');
    if (mensajeDisponibilidad && mensajeDisponibilidad.style.display !== 'none' && 
        mensajeDisponibilidad.innerHTML.includes('NO está disponible')) {
        errores.push('❌ El escenario no está disponible en el horario seleccionado');
        mostrarError('id_escenario', 'Escenario ocupado en este horario');
    }
    
    return errores;
}

// Función para validar el formulario (retorna boolean)
function validarFormulario() {
    const errores = validarFormularioConLista();
    return errores.length === 0;
}

// Detectar cambios en el formulario
function detectarCambios() {
    const inputs = document.querySelectorAll('#sesionForm input, #sesionForm select, #sesionForm textarea');
    inputs.forEach(input => {
        input.addEventListener('change', () => { formModified = true; });
        input.addEventListener('input', () => { formModified = true; });
    });
}

// Inicializar campos condicionales
function initCondicionales() {
    const radioInstitucion = document.querySelector('input[name="tipo_procedencia"][value="institucion"]');
    const radioIndependiente = document.querySelector('input[name="tipo_procedencia"][value="independiente"]');
    const campoInstitucion = document.getElementById('campo_institucion');
    const campoLogo = document.getElementById('campo_logo');
    const inputInstitucionNombre = document.getElementById('nombre_institucion');
    
    const radioMaterialesSi = document.querySelector('input[name="requiere_materiales"][value="si"]');
    const radioMaterialesNo = document.querySelector('input[name="requiere_materiales"][value="no"]');
    const campoMateriales = document.getElementById('campo_materiales');
    const textareaMateriales = document.getElementById('descripcion_materiales');
    
    function toggleCamposProcedencia() {
        if (radioInstitucion && radioInstitucion.checked) {
            if (campoInstitucion) campoInstitucion.style.display = 'flex';
            if (campoLogo) campoLogo.style.display = 'flex';
            if (inputInstitucionNombre) inputInstitucionNombre.required = true;
        } else if (radioIndependiente && radioIndependiente.checked) {
            if (campoInstitucion) campoInstitucion.style.display = 'none';
            if (campoLogo) campoLogo.style.display = 'none';
            if (inputInstitucionNombre) {
                inputInstitucionNombre.required = false;
                inputInstitucionNombre.value = '';
            }
        }
        formModified = true;
    }
    
    function toggleCamposMateriales() {
        if (radioMaterialesSi && radioMaterialesSi.checked) {
            if (campoMateriales) campoMateriales.style.display = 'flex';
            if (textareaMateriales) textareaMateriales.required = true;
        } else if (radioMaterialesNo && radioMaterialesNo.checked) {
            if (campoMateriales) campoMateriales.style.display = 'none';
            if (textareaMateriales) {
                textareaMateriales.required = false;
                textareaMateriales.value = '';
            }
        }
        formModified = true;
    }
    
    if (radioInstitucion && radioIndependiente) {
        radioInstitucion.addEventListener('change', toggleCamposProcedencia);
        radioIndependiente.addEventListener('change', toggleCamposProcedencia);
    }
    
    if (radioMaterialesSi && radioMaterialesNo) {
        radioMaterialesSi.addEventListener('change', toggleCamposMateriales);
        radioMaterialesNo.addEventListener('change', toggleCamposMateriales);
    }
    
    toggleCamposProcedencia();
    toggleCamposMateriales();
}

// Inicializar validaciones en tiempo real
function initValidacionesTiempoReal() {
    // Validación para campos de texto (solo letras)
    const soloLetrasCampos = ['nombre_ponente', 'apellido_paterno', 'apellido_materno'];
    soloLetrasCampos.forEach(campoId => {
        const campo = document.getElementById(campoId);
        if (campo) {
            campo.addEventListener('input', function() {
                if (this.value && !soloLetras(this.value)) {
                    mostrarError(campoId, 'Solo se permiten letras y espacios');
                } else {
                    const errorDiv = document.getElementById(`error-${campoId}`);
                    if (errorDiv) errorDiv.style.display = 'none';
                    this.style.borderColor = '';
                }
                formModified = true;
            });
        }
    });
    
    // Validación para cupo
    const cupoInput = document.getElementById('cupo_audiencia');
    if (cupoInput) {
        cupoInput.addEventListener('input', function() {
            if (this.value && !esNumeroPositivo(this.value)) {
                mostrarError('cupo_audiencia', 'Ingrese un número válido (mayor a 0)');
            } else {
                const errorDiv = document.getElementById('error-cupo_audiencia');
                if (errorDiv) errorDiv.style.display = 'none';
                this.style.borderColor = '';
            }
            formModified = true;
        });
    }
    
    // Validación de archivos
    const fileInputs = ['fotografia', 'logo'];
    fileInputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('change', function() {
                if (this.files.length > 0 && !esImagenValida(this.files[0])) {
                    mostrarError(inputId, 'El archivo debe ser una imagen (JPG, PNG, GIF)');
                } else {
                    const errorDiv = document.getElementById(`error-${inputId}`);
                    if (errorDiv) errorDiv.style.display = 'none';
                    this.style.borderColor = '';
                }
                formModified = true;
            });
        }
    });
    
    // Validación de horas en tiempo real + disponibilidad
    const horaInicio = document.getElementById('hora_inicio');
    const horaFin = document.getElementById('hora_fin');
    
    if (horaInicio) {
        horaInicio.addEventListener('change', () => {
            formModified = true;
            validarHorasEnTiempoReal();
            verificarConDebounce();
        });
        horaInicio.addEventListener('input', () => {
            formModified = true;
            validarHorasEnTiempoReal();
            verificarConDebounce();
        });
    }
    if (horaFin) {
        horaFin.addEventListener('change', () => {
            formModified = true;
            validarHorasEnTiempoReal();
            verificarConDebounce();
        });
        horaFin.addEventListener('input', () => {
            formModified = true;
            validarHorasEnTiempoReal();
            verificarConDebounce();
        });
    }
    
    // Verificar disponibilidad del escenario
    const idEscenario = document.getElementById('id_escenario');
    const fecha = document.getElementById('fecha');
    
    const camposDisponibilidad = [idEscenario, fecha, horaInicio, horaFin];
    
    camposDisponibilidad.forEach(campo => {
        if (campo) {
            campo.addEventListener('change', verificarConDebounce);
            campo.addEventListener('input', verificarConDebounce);
        }
    });
    
    // Actualizar límite de cupo cuando cambie el escenario
    const escenarioSelect = document.getElementById('id_escenario');
    if (escenarioSelect) {
        escenarioSelect.addEventListener('change', function() {
            formModified = true;
            actualizarLimiteCupoPorEscenario();
        });
        // Ejecutar una vez al cargar
        actualizarLimiteCupoPorEscenario();
    }
}

// Configurar evento del formulario
// Configurar evento del formulario
function initFormSubmit() {
    const form = document.getElementById('sesionForm');
    if (!form) return;
    
    const esEdicion = window.location.pathname.includes('/editar/');
    let url = '/admin/sesion/nueva';
    
    if (esEdicion) {
        const id = window.location.pathname.split('/').pop();
        url = `/admin/sesion/editar/${id}`;
    }
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Validar límite de cupo - SOLO ESTA LLAMADA (ya tiene su propio SweetAlert)
        if (!validarLimiteCupoEnvio()) {
            return; // La función ya muestra su propio SweetAlert, solo detenemos el envío
        }
        
        const errores = validarFormularioConLista();
        
        if (errores.length === 0) {
            const result = await Swal.fire({
                title: esEdicion ? '¿Actualizar sesión?' : '¿Guardar sesión?',
                text: 'Verifique que todos los datos sean correctos',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#2d6e3e',
                cancelButtonColor: '#6c757d',
                confirmButtonText: esEdicion ? 'Sí, actualizar' : 'Sí, guardar',
                cancelButtonText: 'Cancelar'
            });
            
            if (result.isConfirmed) {
                formSubmitted = true;
                
                Swal.fire({
                    title: esEdicion ? 'Actualizando...' : 'Guardando...',
                    text: 'Por favor espere',
                    allowOutsideClick: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });
                
                const formData = new FormData(form);
                
                try {
                    const response = await fetch(url, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        await Swal.fire({
                            title: '¡Éxito!',
                            text: data.message || (esEdicion ? 'Sesión actualizada exitosamente' : 'Sesión registrada exitosamente'),
                            icon: 'success',
                            confirmButtonColor: '#2d6e3e'
                        });
                        window.location.href = '/admin/sesiones';
                    } else {
                        await Swal.fire({
                            title: 'Error',
                            text: data.message || (esEdicion ? 'Ocurrió un error al actualizar la sesión' : 'Ocurrió un error al guardar la sesión'),
                            icon: 'error',
                            confirmButtonColor: '#2d6e3e'
                        });
                        formSubmitted = false;
                    }
                } catch (error) {
                    console.error('Error:', error);
                    await Swal.fire({
                        title: 'Error',
                        text: 'Error de conexión con el servidor',
                        icon: 'error'
                    });
                    formSubmitted = false;
                }
            }
        } else {
            let listaErrores = '';
            errores.forEach(error => {
                listaErrores += `• ${error}<br>`;
            });
            
            Swal.fire({
                title: 'Campos con errores',
                html: `<div style="text-align: left;">
                           <p><strong>Por favor corrige:</strong></p>
                           ${listaErrores}
                        </div>`,
                icon: 'error',
                confirmButtonColor: '#2d6e3e'
            });
        }
    });
}
// Configurar botones de cancelar/volver
function initCancelButtons() {
    const btnCancelar = document.getElementById('btnCancelar');
    if (btnCancelar) {
        btnCancelar.addEventListener('click', async function(e) {
            e.preventDefault();
            if (formModified && !formSubmitted) {
                const result = await Swal.fire({
                    title: '¿Descartar cambios?',
                    text: 'Los datos se perderán. ¿Estás seguro?',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#dc3545',
                    cancelButtonColor: '#2d6e3e',
                    confirmButtonText: 'Sí, descartar',
                    cancelButtonText: 'Seguir editando'
                });
                
                if (result.isConfirmed) {
                    window.location.href = '/admin/sesiones';
                }
            } else {
                window.location.href = '/admin/sesiones';
            }
        });
    }
    
    const btnVolver = document.getElementById('btnVolverListado');
    if (btnVolver) {
        btnVolver.addEventListener('click', async function(e) {
            e.preventDefault();
            if (formModified && !formSubmitted) {
                const result = await Swal.fire({
                    title: '¿Descartar cambios?',
                    text: 'Los datos se perderán. ¿Estás seguro?',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#dc3545',
                    cancelButtonColor: '#2d6e3e',
                    confirmButtonText: 'Sí, descartar',
                    cancelButtonText: 'Seguir editando'
                });
                
                if (result.isConfirmed) {
                    window.location.href = btnVolver.href;
                }
            } else {
                window.location.href = btnVolver.href;
            }
        });
    }
}

// Inicializar todo
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM cargado - Inicializando validaciones");
    detectarCambios();
    initCondicionales();
    initValidacionesTiempoReal();
    initFormSubmit();
    initCancelButtons();
});