// static/js/global.js
// === MODO NOCTURNO GLOBAL ===
(function() {
    // Función para aplicar el modo según localStorage
    function aplicarModoNocturno() {
        const isDark = localStorage.getItem('darkMode') === 'enabled';
        if (isDark) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
    }
    
    // Función para alternar el modo
    function toggleModoNocturno() {
        const isDark = document.body.classList.contains('dark-mode');
        if (isDark) {
            localStorage.setItem('darkMode', 'disabled');
            document.body.classList.remove('dark-mode');
        } else {
            localStorage.setItem('darkMode', 'enabled');
            document.body.classList.add('dark-mode');
        }
        
        // Actualizar icono si existe el botón
        actualizarIconoModo();
    }
    
    // Actualizar el icono del botón según el modo actual
    function actualizarIconoModo() {
        const themeToggle = document.getElementById('themeToggle');
        if (!themeToggle) return;
        
        const icon = themeToggle.querySelector('i');
        if (!icon) return;
        
        const isDark = document.body.classList.contains('dark-mode');
        if (isDark) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    }
    
    // Configurar el botón de tema si existe
    function configurarBotonTema() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            const newToggle = themeToggle.cloneNode(true);
            themeToggle.parentNode.replaceChild(newToggle, themeToggle);
            
            newToggle.addEventListener('click', (e) => {
                e.preventDefault();
                toggleModoNocturno();
            });
        }
    }
    
    // Inicializar cuando el DOM esté listo
    document.addEventListener('DOMContentLoaded', function() {
        aplicarModoNocturno();
        configurarBotonTema();
        actualizarIconoModo();
    });
    
    window.toggleModoNocturno = toggleModoNocturno;
})();

// === CIERRE DE SESIÓN CON SWEETALERT ===
document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const isDarkMode = document.body.classList.contains('dark-mode');
            
            Swal.fire({
                title: '¿Cerrar sesión?',
                text: '¿Estás seguro/a de que deseas cerrar la sesión?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#2d6e3e',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Sí, cerrar sesión',
                cancelButtonText: 'Cancelar',
                background: isDarkMode ? '#1e1e1e' : '#ffffff',
                color: isDarkMode ? '#f0f0f0' : '#1a2a1e'
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        title: '¡Sesión cerrada!',
                        text: 'Redirigiendo al inicio de sesión...',
                        icon: 'success',
                        timer: 1500,
                        showConfirmButton: false,
                        didOpen: () => {
                            Swal.showLoading();
                        }
                    }).then(() => {
                        window.location.replace('/logout');
                    });
                }
            });
        });
    }
});

// ============================================
// === PROTECCIÓN CONTRA FLECHAS DEL NAVEGADOR ===
// ============================================

// Verificar si es una página pública
function esPaginaPublica() {
    const paginasPublicas = [
        '/', '/login', '/olvide-password', '/recuperar-password',
        '/cambiar-password', '/logout'
    ];
    const ruta = window.location.pathname;
    return paginasPublicas.includes(ruta) || ruta === '/';
}

// Verificar si es una página protegida
function esPaginaProtegida() {
    return window.location.pathname.startsWith('/admin/') ||
           window.location.pathname.startsWith('/alumno/') ||
           window.location.pathname.includes('/dashboard') ||
           window.location.pathname.includes('/sesiones') ||
           window.location.pathname.includes('/usuarios') ||
           window.location.pathname.includes('/agenda');
}

// Verificar sesión con el servidor
async function verificarSesionBackend() {
    try {
        const response = await fetch('/check-session', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache, no-store'
            },
            credentials: 'same-origin'
        });
        
        if (response.status === 401 || !response.ok) {
            return false;
        }
        
        const data = await response.json();
        return data.authenticated === true;
    } catch (error) {
        console.error('Error verificando sesión:', error);
        return false;
    }
}

// Redirigir al login
function redirigirALogin() {
    if (window.location.pathname === '/login') return;
    console.log('Sesión inválida, redirigiendo a login...');
    window.location.replace('/login');
}

// Detectar flechas del navegador
function detectarFlechasNavegador() {
    window.addEventListener('pageshow', async function(event) {
        if (event.persisted && esPaginaProtegida()) {
            console.log('⚠️ Navegación con flechas detectada');
            const sesionValida = await verificarSesionBackend();
            if (!sesionValida) {
                redirigirALogin();
            }
        }
    });
}

// Prevenir botón atrás
function prevenirVolverAtras() {
    if (!esPaginaProtegida()) return;
    
    history.pushState(null, null, location.href);
    
    window.addEventListener('popstate', async function() {
        console.log('⚠️ Botón atrás detectado');
        const sesionValida = await verificarSesionBackend();
        if (sesionValida) {
            history.pushState(null, null, location.href);
        } else {
            redirigirALogin();
        }
    });
}

// Verificar sesión al cargar
async function verificarSesionAlCargar() {
    if (esPaginaProtegida()) {
        console.log('Página protegida, verificando sesión...');
        const sesionValida = await verificarSesionBackend();
        if (!sesionValida) {
            redirigirALogin();
        }
    }
}

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    verificarSesionAlCargar();
    detectarFlechasNavegador();
    prevenirVolverAtras();
});

// Protección adicional - Forzar recarga si la página viene de caché
window.addEventListener('pageshow', function(event) {
    if (event.persisted && esPaginaProtegida()) {
        window.location.reload();
    }
});

// static/js/global.js
document.addEventListener('DOMContentLoaded', function() {
    // Limpiar campos de login en todas las páginas
    limpiarFormularios();
});

function limpiarFormularios() {
    // Buscar formularios de login
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        if (form.action.includes('login')) {
            form.reset();
        }
    });
    
    // Limpiar campos específicos
    const emailInputs = document.querySelectorAll('input[type="email"]');
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    emailInputs.forEach(input => {
        input.value = '';
    });
    
    passwordInputs.forEach(input => {
        input.value = '';
    });
}

// Prevenir autocompletado del navegador
if (typeof window !== 'undefined') {
    // Deshabilitar autocompletado para todos los formularios
    document.querySelectorAll('form').forEach(form => {
        form.setAttribute('autocomplete', 'off');
    });
}