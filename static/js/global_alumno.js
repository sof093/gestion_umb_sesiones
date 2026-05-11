// ============================================================
// GLOBAL JS - UES San José del Rincón
// Funciones compartidas: dark mode, logout, navbar toggle
// ============================================================

// === MODO OSCURO GLOBAL ===
(function() {
    function aplicarModo() {
        const isDark = localStorage.getItem('ues-theme') === 'dark';
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        
        // Actualizar icono si existe
        const themeIcon = document.getElementById('themeIcon');
        if (themeIcon) {
            themeIcon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
    
    function toggleModo() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const newTheme = isDark ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('ues-theme', newTheme);
        
        // Actualizar icono
        const themeIcon = document.getElementById('themeIcon');
        if (themeIcon) {
            themeIcon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
    
    // Configurar botón de tema
    function configurarBotonTema() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', (e) => {
                e.preventDefault();
                toggleModo();
            });
        }
    }
    
    document.addEventListener('DOMContentLoaded', () => {
        aplicarModo();
        configurarBotonTema();
    });
})();

// === CIERRE DE SESIÓN CON SWEETALERT ===
document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.getElementById('logoutBtn');
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            
            Swal.fire({
                title: '¿Cerrar sesión?',
                text: '¿Estás seguro/a de que deseas cerrar la sesión?',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#2d5a3d',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Sí, cerrar sesión',
                cancelButtonText: 'Cancelar',
                background: isDark ? '#172a1f' : '#ffffff',
                color: isDark ? '#e8f4ec' : '#1a2e22'
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        title: '¡Sesión cerrada!',
                        text: 'Redirigiendo al inicio de sesión...',
                        icon: 'success',
                        timer: 1500,
                        showConfirmButton: false
                    }).then(() => {
                        window.location.href = '/logout';
                    });
                }
            });
        });
    }
});

// === NAVBAR RESPONSIVO (MENÚ HAMBURGUESA) ===
document.addEventListener('DOMContentLoaded', function() {
    const navbarToggle = document.getElementById('navbarToggle');
    const navbarCollapse = document.getElementById('navbarCollapse');
    
    if (navbarToggle && navbarCollapse) {
        navbarToggle.addEventListener('click', () => {
            navbarCollapse.classList.toggle('open');
            
            const icon = navbarToggle.querySelector('i');
            if (navbarCollapse.classList.contains('open')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
        
        // Cerrar menú al hacer clic en un enlace
        document.querySelectorAll('.nav-link-pill, .btn-icon-nav').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    navbarCollapse.classList.remove('open');
                    const icon = navbarToggle.querySelector('i');
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            });
        });
    }
    
    // Cerrar menú al redimensionar a desktop
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768 && navbarCollapse) {
            navbarCollapse.classList.remove('open');
            const icon = navbarToggle?.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        }
    });
});