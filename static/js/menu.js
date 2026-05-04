// === MENÚ HAMBURGUESA ===
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menuToggle');
    const navLinks = document.getElementById('navLinks');
    
    if (!menuToggle || !navLinks) return;
    
    // Función para cerrar el menú
    function closeMenu() {
        menuToggle.classList.remove('active');
        navLinks.classList.remove('active');
    }
    
    // Función para abrir el menú
    function openMenu() {
        menuToggle.classList.add('active');
        navLinks.classList.add('active');
    }
    
    // Alternar menú al hacer clic en el botón
    menuToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        if (navLinks.classList.contains('active')) {
            closeMenu();
        } else {
            openMenu();
        }
    });
    
    // Cerrar menú al hacer clic en un enlace
    const links = navLinks.querySelectorAll('a');
    links.forEach(link => {
        link.addEventListener('click', closeMenu);
    });
    
    // Cerrar menú al hacer clic fuera de él (solo en móvil)
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            const isClickInside = navLinks.contains(event.target) || menuToggle.contains(event.target);
            if (!isClickInside && navLinks.classList.contains('active')) {
                closeMenu();
            }
        }
    });
    
    // Cerrar menú al redimensionar a desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeMenu();
        }
    });
});