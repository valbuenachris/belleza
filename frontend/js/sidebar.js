const Sidebar = {
    async init() {
        await this.loadComponent();
        this.configure();
    },

    async loadComponent() {
        try {
            const response = await fetch('components/sidebar.html');
            const html = await response.text();
            const container = document.getElementById('sidebar-container');
            if (container) {
                container.innerHTML = html;
            }
        } catch (error) {
            console.error('Error cargando sidebar:', error);
        }
    },

    configure() {
        const user = Auth.getCurrentUser();
        if (!user) return;

        document.getElementById('userName').textContent = user.nombre + ' ' + user.apellido;
        const roleLabels = { superadmin: 'Super Administrador', admin: 'Administrador', manager: 'Gerente', receptionist: 'Recepcionista', therapist: 'Terapeuta' };
        document.getElementById('userRole').textContent = roleLabels[user.rol] || user.rol;
        document.getElementById('userAvatar').textContent = (user.nombre[0] + user.apellido[0]).toUpperCase();

        const tenantInfoEl = document.getElementById('tenantInfo');
        const sidebarNavEl = document.getElementById('sidebarNav');

        if (user.rol === 'superadmin') {
            tenantInfoEl.innerHTML = `<p class="tenant-label">Administración</p><p class="tenant-name">Global</p><span class="tenant-plan">Super Admin</span>`;
            sidebarNavEl.innerHTML = `
                <a href="index.html" class="nav-item" data-page="dashboard"><span class="nav-icon">📊</span><span>Dashboard</span></a>
                <a href="tenants.html" class="nav-item" data-page="tenants"><span class="nav-icon">🏢</span><span>SPAs / Tenants</span></a>
                <a href="admin-users.html" class="nav-item" data-page="users"><span class="nav-icon">👥</span><span>Usuarios</span></a>
                <a href="appointments.html" class="nav-item" data-page="appointments"><span class="nav-icon">📅</span><span>Citas</span></a>
                <a href="patients.html" class="nav-item" data-page="patients"><span class="nav-icon">👤</span><span>Pacientes</span></a>
                <a href="settings.html" class="nav-item" data-page="settings"><span class="nav-icon">⚙️</span><span>Configuración</span></a>
                <a href="documentation.html" class="nav-item" data-page="documentation"><span class="nav-icon">📚</span><span>Documentación</span></a>
            `;
        } else {
            const tenant = Auth.getTenant();
            tenantInfoEl.innerHTML = `<p class="tenant-label">Tenant Activo</p><p class="tenant-name">${tenant ? tenant.nombre : 'N/A'}</p><span class="tenant-plan">${tenant ? tenant.plan : 'basic'}</span>`;
            sidebarNavEl.innerHTML = `
                <a href="index.html" class="nav-item" data-page="dashboard"><span class="nav-icon"></span><span>Dashboard</span></a>
                <a href="#" class="nav-item" data-page="appointments"><span class="nav-icon">📅</span><span>Citas</span></a>
                <a href="#" class="nav-item" data-page="patients"><span class="nav-icon">👤</span><span>Pacientes</span></a>
                <a href="#" class="nav-item" data-page="services"><span class="nav-icon">💆</span><span>Servicios</span></a>
                <a href="#" class="nav-item" data-page="users"><span class="nav-icon">🔑</span><span>Usuarios</span></a>
                <a href="settings.html" class="nav-item" data-page="settings"><span class="nav-icon">⚙️</span><span>Configuración</span></a>
            `;
        }

        this.setActivePage();
        this.setupEvents();
    },

    setActivePage() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const pageMap = { 
            'index.html': 'dashboard', 
            'tenants.html': 'tenants', 
            'admin-users.html': 'users',
            'appointments.html': 'appointments',
            'patients.html': 'patients',
            'settings.html': 'settings',
            'documentation.html': 'documentation'
        };
        const activePage = pageMap[currentPage] || 'dashboard';

        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === activePage);
        });
    },

    setupEvents() {
        document.getElementById('btnLogout')?.addEventListener('click', () => {
            if (confirm('¿Estás seguro de que deseas cerrar sesión?')) Auth.logout();
        });
        document.getElementById('menuToggle')?.addEventListener('click', () => document.getElementById('sidebar')?.classList.add('open'));
        document.getElementById('sidebarClose')?.addEventListener('click', () => document.getElementById('sidebar')?.classList.remove('open'));
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (Auth.isAuthenticated()) Sidebar.init();
});
