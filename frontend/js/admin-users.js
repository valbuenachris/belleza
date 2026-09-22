// ============================================================
// frontend/js/admin-users.js - Gestión de Usuarios
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

    // Cargar usuarios
    loadUsers();

    // Configurar event listeners
    setupEventListeners();

    console.log('✅ Página de Usuarios cargada');
});

function loadUserData(user) {
    const userNameEl = document.getElementById('userName');
    if (userNameEl) userNameEl.textContent = user.nombre + ' ' + user.apellido;

    const userRoleEl = document.getElementById('userRole');
    if (userRoleEl) userRoleEl.textContent = 'Super Administrador';

    const userAvatarEl = document.getElementById('userAvatar');
    if (userAvatarEl) userAvatarEl.textContent = user.nombre[0] + user.apellido[0];
}

function loadUsers() {
    // Datos de ejemplo - en producción vendrían de la API
    const users = [
        {
            id: '1',
            username: 'superadmin',
            email: 'superadmin@spa.com',
            nombre: 'Super',
            apellido: 'Administrador',
            telefono: '+57 300 123 4567',
            rol: 'superadmin',
            activo: true
        },
        {
            id: '2',
            username: 'admin',
            email: 'admin@demo.com',
            nombre: 'María',
            apellido: 'González',
            telefono: '+57 300 987 6543',
            rol: 'admin',
            activo: true
        },
        {
            id: '3',
            username: 'recepcionista',
            email: 'recepcion@demo.com',
            nombre: 'Laura',
            apellido: 'Martínez',
            telefono: '+57 300 456 7890',
            rol: 'receptionist',
            activo: true
        },
        {
            id: '4',
            username: 'terapeuta1',
            email: 'terapeuta@demo.com',
            nombre: 'Ana',
            apellido: 'Rodríguez',
            telefono: '+57 300 111 2233',
            rol: 'therapist',
            activo: true
        }
    ];

    renderUsers(users);
}

function renderUsers(users) {
    const grid = document.getElementById('usersGrid');
    if (!grid) return;

    const roleConfig = {
        superadmin: { label: 'Super Administrador', color: 'danger', icon: '🛡️' },
        admin: { label: 'Administrador', color: 'primary', icon: '' },
        manager: { label: 'Gerente', color: 'warning', icon: '' },
        receptionist: { label: 'Recepcionista', color: 'secondary', icon: '📞' },
        therapist: { label: 'Terapeuta', color: 'info', icon: '💆' }
    };

    grid.innerHTML = users.map(user => {
        const config = roleConfig[user.rol] || roleConfig.admin;
        const initials = (user.nombre[0] + user.apellido[0]).toUpperCase();
        
        return `
            <div class="user-card">
                <div class="user-card-header">
                    <div class="user-avatar-large">${initials}</div>
                    <div class="user-card-actions">
                        <button class="btn-icon-small" title="Editar">✏️</button>
                        <button class="btn-icon-small" title="Eliminar">🗑️</button>
                    </div>
                </div>
                <div class="user-card-body">
                    <h3 class="user-card-name">${user.nombre} ${user.apellido}</h3>
                    <p class="user-card-username">@${user.username}</p>
                    <p class="user-card-info">📧 ${user.email}</p>
                    <p class="user-card-info">📞 ${user.telefono}</p>
                </div>
                <div class="user-card-footer">
                    <span class="badge badge-${config.color}">${config.icon} ${config.label}</span>
                    <span class="status-badge ${user.activo ? 'active' : 'inactive'}">
                        ${user.activo ? '✓ Activo' : '✕ Inactivo'}
                    </span>
                </div>
            </div>
        `;
    }).join('');
}

function setupEventListeners() {
    // Modal
    const modal = document.getElementById('newUserModal');
    const btnNewUser = document.getElementById('btnNewUser');
    const btnCancel = document.getElementById('cancelUser');
    const btnSave = document.getElementById('saveUser');

    if (btnNewUser) {
        btnNewUser.addEventListener('click', () => {
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
            alert('Funcionalidad de creación de usuario en desarrollo');
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
