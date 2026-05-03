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