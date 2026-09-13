// ============================================================
// frontend/js/app.js - Lógica principal de la aplicación
// Inicialización, navegación, y componentes globales
// ============================================================

/**
 * Aplicación principal del SPA Management System.
 * Maneja la navegación, inicialización de componentes, y eventos globales.
 */
const App = {
    /**
     * Inicializa la aplicación.
     */
    init() {
        // Verificar autenticación
        if (!Auth.isAuthenticated()) {
            window.location.href = 'login.html';
            return;
        }

        // Cargar datos del usuario
        this.loadUserData();
        
        // Configurar navegación
        this.setupNavigation();
        
        // Configurar sidebar mobile
        this.setupMobileSidebar();
        
        // Configurar logout
        this.setupLogout();
        
        // Mostrar fecha actual
        this.showCurrentDate();
        
        // Generar gráfico de barras
        this.renderWeeklyChart();
        
        console.log('✅ SPA Management System inicializado');
    },

    /**
     * Carga y muestra los datos del usuario y tenant.
     */
    loadUserData() {
        const user = Auth.getCurrentUser();
        const tenant = Auth.getTenant();

        if (user) {
            // Nombre de usuario
            const userNameEl = document.getElementById('userName');
            if (userNameEl) {
                userNameEl.textContent = `${user.nombre} ${user.apellido}`;
            }

            // Rol del usuario
            const userRoleEl = document.getElementById('userRole');
            if (userRoleEl) {
                const roleLabels = {
                    superadmin: 'Super Administrador',
                    admin: 'Administrador',
                    manager: 'Gerente',
                    receptionist: 'Recepcionista',
                    therapist: 'Terapeuta',
                };
                userRoleEl.textContent = roleLabels[user.rol] || user.rol;
            }

            // Avatar (iniciales)
            const userAvatarEl = document.getElementById('userAvatar');
            if (userAvatarEl) {
                userAvatarEl.textContent = `${user.nombre[0]}${user.apellido[0]}`;
            }

            // Welcome message
            const welcomeNameEl = document.getElementById('welcomeName');
            if (welcomeNameEl) {
                welcomeNameEl.textContent = user.nombre;
            }
        }

        if (tenant) {
            // Nombre del tenant
            const tenantNameEl = document.getElementById('tenantName');
            if (tenantNameEl) {
                tenantNameEl.textContent = tenant.nombre;
            }

            // Plan del tenant
            const tenantPlanEl = document.getElementById('tenantPlan');
            if (tenantPlanEl) {
                tenantPlanEl.textContent = tenant.plan;
            }

            // Welcome subtitle
            const welcomeSubtitleEl = document.getElementById('welcomeSubtitle');
            if (welcomeSubtitleEl) {
                welcomeSubtitleEl.textContent = `Panel de ${tenant.nombre}`;
            }
        }
    },

    /**
     * Configura la navegación del sidebar.
     */
    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remover clase active de todos
                navItems.forEach(nav => nav.classList.remove('active'));
                
                // Agregar clase active al clickeado
                item.classList.add('active');
                
                // Navegar a la página (en una SPA real se cargaría el contenido)
                const page = item.dataset.page;
                this.navigateTo(page);
                
                // Cerrar sidebar en mobile
                this.closeMobileSidebar();
            });
        });
    },

    /**
     * Navega a una página específica.
     * @param {string} page - Nombre de la página
     */
    navigateTo(page) {
        // En una implementación completa, esto cargaría el contenido dinámicamente
        // Por ahora, solo mostramos un toast informativo
        const pageNames = {
            dashboard: 'Dashboard',
            appointments: 'Citas',
            patients: 'Pacientes',
            services: 'Servicios',
            users: 'Usuarios',
            settings: 'Configuración',
        };
        
        const name = pageNames[page] || page;
        this.showToast(`Navegando a ${name}`, 'info');
    },

    /**
     * Configura el sidebar para mobile.
     */
    setupMobileSidebar() {
        const menuToggle = document.getElementById('menuToggle');
        const sidebarClose = document.getElementById('sidebarClose');
        const sidebar = document.getElementById('sidebar');

        if (menuToggle) {
            menuToggle.addEventListener('click', () => {
                sidebar.classList.add('open');
            });
        }

        if (sidebarClose) {
            sidebarClose.addEventListener('click', () => {
                this.closeMobileSidebar();
            });
        }

        // Cerrar al hacer click fuera
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                    this.closeMobileSidebar();
                }
            }
        });
    },

    /**
     * Cierra el sidebar en mobile.
     */
    closeMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
        }
    },

    /**
     * Configura el botón de logout.
     */
    setupLogout() {
        const btnLogout = document.getElementById('btnLogout');
        if (btnLogout) {
            btnLogout.addEventListener('click', () => {
                if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
                    Auth.logout();
                }
            });
        }
    },

    /**
     * Muestra la fecha actual formateada.
     */
    showCurrentDate() {
        const dateEl = document.getElementById('currentDate');
        if (dateEl) {
            const now = new Date();
            const options = { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            };
            dateEl.textContent = now.toLocaleDateString('es-ES', options);
        }
    },

    /**
     * Renderiza el gráfico de barras semanal.
     */
    renderWeeklyChart() {
        const chartContainer = document.getElementById('weeklyChart');
        if (!chartContainer) return;

        const data = [
            { day: 'Lun', value: 8 },
            { day: 'Mar', value: 12 },
            { day: 'Mié', value: 10 },
            { day: 'Jue', value: 15 },
            { day: 'Vie', value: 9 },
            { day: 'Sáb', value: 7 },
            { day: 'Dom', value: 3 },
        ];

        const maxValue = Math.max(...data.map(d => d.value));

        chartContainer.innerHTML = data.map(item => {
            const height = (item.value / maxValue) * 100;
            return `
                <div class="chart-bar-item">
                    <div class="chart-bar" style="height: ${height}%" title="${item.value} citas"></div>
                    <span class="chart-bar-label">${item.day}</span>
                </div>
            `;
        }).join('');
    },

    /**
     * Muestra una notificación toast.
     * @param {string} message - Mensaje a mostrar
     * @param {string} type - Tipo: success, error, warning, info
     * @param {number} duration - Duración en ms (default: 3000)
     */
    showToast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span>${message}</span>
        `;

        container.appendChild(toast);

        // Remover después de la duración
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Muestra/oculta un loader global.
     * @param {boolean} show - True para mostrar, false para ocultar
     */
    showLoader(show) {
        let loader = document.getElementById('globalLoader');
        
        if (show) {
            if (!loader) {
                loader = document.createElement('div');
                loader.id = 'globalLoader';
                loader.className = 'global-loader';
                loader.innerHTML = '<div class="spinner spinner-dark"></div>';
                document.body.appendChild(loader);
            }
            loader.style.display = 'flex';
        } else {
            if (loader) {
                loader.style.display = 'none';
            }
        }
    },
};

// ============================================================
// Inicializar la aplicación cuando el DOM esté listo
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// ============================================================
// Event listeners globales
// ============================================================

// Escuchar evento de login
document.addEventListener('spa:login', (e) => {
    console.log('Usuario autenticado:', e.detail.user?.email);
});

// Escuchar evento de logout
document.addEventListener('spa:logout', () => {
    console.log('Sesión cerrada');
});

// Manejar errores globales
window.addEventListener('error', (e) => {
    console.error('Error global:', e.error);
});

// Manejar promesas rechazadas
window.addEventListener('unhandledrejection', (e) => {
    console.error('Promesa rechazada:', e.reason);
    e.preventDefault();
});
