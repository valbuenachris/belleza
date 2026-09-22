// ============================================================
// frontend/js/tenants.js - Gestión de Tenants
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    // Verificar autenticación
    if (!Auth.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    // Verificar que sea superadmin
    const user = Auth.getCurrentUser();
    if (user.rol !== 'superadmin') {
        window.location.href = 'index.html';
        return;
    }

    // Cargar datos del usuario
    loadUserData(user);

    // Cargar tenants
    loadTenants();

    // Configurar event listeners
    setupEventListeners();

    console.log('✅ Página de Tenants cargada');
});

function loadUserData(user) {
    const userNameEl = document.getElementById('userName');
    if (userNameEl) userNameEl.textContent = user.nombre + ' ' + user.apellido;

    const userRoleEl = document.getElementById('userRole');
    if (userRoleEl) userRoleEl.textContent = 'Super Administrador';

    const userAvatarEl = document.getElementById('userAvatar');
    if (userAvatarEl) userAvatarEl.textContent = user.nombre[0] + user.apellido[0];
}

function loadTenants() {
    // Datos de ejemplo - en producción vendrían de la API
    const tenants = [
        {
            id: '1',
            nombre: 'Serenity Spa & Wellness',
            email: 'info@serenityspa.com',
            subdominio: 'demo',
            plan: 'professional',
            usuarios: 6,
            limiteUsuarios: 10,
            activo: true
        },
        {
            id: '2',
            nombre: 'Zen Garden Spa',
            email: 'contacto@zengarden.com',
            subdominio: 'zengarden',
            plan: 'basic',
            usuarios: 6,
            limiteUsuarios: 5,
            activo: true
        },
        {
            id: '3',
            nombre: 'Bella Vita Estética',
            email: 'admin@bellavita.com',
            subdominio: 'bellavita',
            plan: 'enterprise',
            usuarios: 6,
            limiteUsuarios: 50,
            activo: true
        }
    ];

    renderTenants(tenants);
    updateStats(tenants);
}

function renderTenants(tenants) {
    const tbody = document.getElementById('tenantsTableBody');
    if (!tbody) return;

    tbody.innerHTML = tenants.map(tenant => `
        <tr>
            <td>
                <div class="tenant-cell">
                    <div class="tenant-icon">🏢</div>
                    <div>
                        <div class="tenant-name">${tenant.nombre}</div>
                        <div class="tenant-email">${tenant.email}</div>
                    </div>
                </div>
            </td>
            <td>
                <span class="subdomain">🌐 ${tenant.subdominio}.spasystem.com</span>
            </td>
            <td>
                <span class="badge badge-${tenant.plan}">${tenant.plan.charAt(0).toUpperCase() + tenant.plan.slice(1)}</span>
            </td>
            <td>
                <span class="users-count">👥 ${tenant.usuarios} / ${tenant.limiteUsuarios}</span>
            </td>
            <td>
                <span class="status-badge ${tenant.activo ? 'active' : 'inactive'}">
                    ${tenant.activo ? '✓ Activo' : ' Inactivo'}
                </span>
            </td>
            <td>
                <div class="actions">
                    <button class="btn-icon" title="Más opciones">⋮</button>
                    <button class="btn-icon" title="Editar">✏️</button>
                    <button class="btn-icon" title="Eliminar">🗑️</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function updateStats(tenants) {
    const total = tenants.length;
    const activos = tenants.filter(t => t.activo).length;
    const enterprise = tenants.filter(t => t.plan === 'enterprise').length;

    document.getElementById('totalTenants').textContent = total;
    document.getElementById('activeTenants').textContent = activos;
    document.getElementById('enterpriseTenants').textContent = enterprise;
}

function setupEventListeners() {
    // Modal
    const modal = document.getElementById('newTenantModal');
    const btnNewTenant = document.getElementById('btnNewTenant');
    const btnCancel = document.getElementById('cancelTenant');
    const btnSave = document.getElementById('saveTenant');

    if (btnNewTenant) {
        btnNewTenant.addEventListener('click', () => {
            modal.style.display = 'flex';
        });
    }

    if (btnCancel) {
        btnCancel.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    if (btnSave) {
        btnSave.addEventListener('click', () => {
            // Aquí iría la lógica para crear el tenant
            alert('Funcionalidad de creación de tenant en desarrollo');
            modal.style.display = 'none';
        });
    }

    // Cerrar modal al hacer clic fuera
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

    // Sidebar mobile
    const menuToggle = document.getElementById('menuToggle');
    const sidebarClose = document.getElementById('sidebarClose');
    const sidebar = document.getElementById('sidebar');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => sidebar.classList.add('open'));
    }
    if (sidebarClose) {
        sidebarClose.addEventListener('click', () => sidebar.classList.remove('open'));
    }

    // Logout
    const btnLogout = document.getElementById('btnLogout');
    if (btnLogout) {
        btnLogout.addEventListener('click', () => {
            if (confirm('¿Estás seguro de que deseas cerrar sesión?')) {
                Auth.logout();
            }
        });
    }
}
