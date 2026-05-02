
   
        // === MODO NOCTURNO ===
        const themeToggle = document.getElementById('themeToggle');
        const body = document.body;
        const moonIcon = themeToggle.querySelector('i');

        // Verificar modo guardado
        if (localStorage.getItem('darkMode') === 'enabled') {
            body.classList.add('dark-mode');
            moonIcon.classList.remove('fa-moon');
            moonIcon.classList.add('fa-sun');
        }

        themeToggle.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            if (body.classList.contains('dark-mode')) {
                localStorage.setItem('darkMode', 'enabled');
                moonIcon.classList.remove('fa-moon');
                moonIcon.classList.add('fa-sun');
            } else {
                localStorage.setItem('darkMode', 'disabled');
                moonIcon.classList.remove('fa-sun');
                moonIcon.classList.add('fa-moon');
            }
        });

        // === NOMBRE DEL ADMIN (desde base de datos) ===
        // Aquí puedes cargar el nombre real desde Flask/Jinja
        // Ejemplo: <span class="user-name">{{ admin_nombre }}</span>
        const adminNameSpan = document.getElementById('adminName');
        
        // Simulación de nombre desde backend (reemplazar con variable de Flask)
        // Para Flask usar: {{ admin_nombre | default('Admin') }}
        const adminNombreReal = "Dr. Roberto Martínez"; // Este valor vendría de la base de datos
        if (adminNombreReal) {
            adminNameSpan.textContent = adminNombreReal;
        }

        // === NAVEGACIÓN ENTRE SESIONES Y USUARIOS ===
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                
                // Actualizar clase activa
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
                
                // Simular cambio de contenido (aquí cargarías diferentes vistas)
                if (page === 'sesiones') {
                    mostrarVistaSesiones();
                } else if (page === 'usuarios') {
                    mostrarVistaUsuarios();
                }
            });
        });

        function mostrarVistaSesiones() {
            // Mantener el contador de sesiones visible
            document.querySelector('.stats-card').style.display = 'flex';
            document.querySelector('.image-card').style.display = 'block';
            document.querySelector('.page-title').innerHTML = 'Gestión de la jornada<br>académica y cultural';
            actualizarTotalSesiones(10);
        }

        function mostrarVistaUsuarios() {
            // Cambiar contenido para usuarios
            document.querySelector('.stats-card').style.display = 'flex';
            document.querySelector('.image-card').style.display = 'block';
            document.querySelector('.page-title').innerHTML = 'Gestión de usuarios<br>del sistema';
            
            // Cambiar el contenido del recuadro
            const statsTitle = document.querySelector('.stats-title');
            statsTitle.innerHTML = '<i class="fas fa-users" style="color: #D0A612; margin-right: 8px;"></i> Total de usuarios registrados';
            
            const statsNumber = document.querySelector('.stats-number');
            statsNumber.textContent = '24';
            
            const statsLabel = document.querySelector('.stats-label');
            statsLabel.textContent = 'Usuarios activos en el sistema';
        }

        function actualizarTotalSesiones(total) {
            const statsNumber = document.querySelector('.stats-number');
            if (statsNumber) statsNumber.textContent = total;
        }

        // === CIERRE DE SESIÓN ===
        const logoutBtn = document.getElementById('logoutBtn');
        logoutBtn.addEventListener('click', () => {
            // Redirigir al login (Flask)
            window.location.href = "{{ url_for('logout') }}";
            // Si no usas Flask, redirige a login.html
            // window.location.href = "/login";
        });

        // === CARGAR DATOS DESDE FLASK (ejemplo) ===
        // Puedes pasar variables desde Flask:
        // - total_sesiones
        // - admin_nombre
        // Ejemplo de uso con Jinja:
        /*
        {% if total_sesiones %}
            document.getElementById('totalSesiones').textContent = {{ total_sesiones }};
        {% endif %}
        
        {% if admin_nombre %}
            document.getElementById('adminName').textContent = "{{ admin_nombre }}";
        {% endif %}
        */
        
        // Si la imagen no carga, poner una por defecto
        const universityImg = document.querySelector('.university-image');
        if (universityImg) {
            universityImg.addEventListener('error', function() {
                this.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='875' height='477' viewBox='0 0 875 477'%3E%3Crect width='875' height='477' fill='%231a3a2a'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='24' font-family='Playfair Display'%3EUES San José del Rincón%3C/text%3E%3C/svg%3E";
            });
        }