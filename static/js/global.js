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
            // Remover event listeners previos para evitar duplicados
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
    
    // Exponer función global por si se necesita
    window.toggleModoNocturno = toggleModoNocturno;
})();

// === CIERRE DE SESIÓN CON SWEETALERT ===
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
                    // Mostrar mensaje de éxito
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
                        // Redirigir al logout de Flask
                        window.location.href = '/logout';
                    });
                }
            });
        });
    }
});