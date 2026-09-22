// ============================================================
// frontend/js/settings.js - Configuración del Sistema (Funcional)
// ============================================================

const Settings = {
    // Clave para localStorage
    STORAGE_KEY: 'spa_settings',

    init() {
        if (!Auth.isAuthenticated()) {
            window.location.href = 'login.html';
            return;
        }

        this.loadSettings();
        this.setupTabs();
        this.setupFormHandlers();
        this.setupToggleHandlers();
        console.log('✅ Página de Configuración cargada');
    },

    loadSettings() {
        const saved = localStorage.getItem(this.STORAGE_KEY);
        if (saved) {
            const settings = JSON.parse(saved);
            
            // Cargar valores en formularios
            if (settings.systemName) document.getElementById('systemName').value = settings.systemName;
            if (settings.contactEmail) document.getElementById('contactEmail').value = settings.contactEmail;
            if (settings.timezone) document.getElementById('timezone').value = settings.timezone;
            if (settings.language) document.getElementById('language').value = settings.language;
            if (settings.theme) document.getElementById('theme').value = settings.theme;
            if (settings.dateFormat) document.getElementById('dateFormat').value = settings.dateFormat;
        }
    },

    saveSettings() {
        const settings = {
            systemName: document.getElementById('systemName').value,
            contactEmail: document.getElementById('contactEmail').value,
            timezone: document.getElementById('timezone').value,
            language: document.getElementById('language').value,
            theme: document.getElementById('theme').value,
            dateFormat: document.getElementById('dateFormat').value,
            notifications: {
                newAppointments: document.querySelector('[data-notif="newAppointments"]')?.checked || false,
                reminders: document.querySelector('[data-notif="reminders"]')?.checked || false,
                cancellations: document.querySelector('[data-notif="cancellations"]')?.checked || false,
                systemAlerts: document.querySelector('[data-notif="systemAlerts"]')?.checked || false,
                updates: document.querySelector('[data-notif="updates"]')?.checked || false
            }
        };

        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(settings));
        this.showNotification('Configuración guardada exitosamente', 'success');
    },

    setupTabs() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabPanels = document.querySelectorAll('.tab-panel');

        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;

                tabButtons.forEach(b => b.classList.remove('active'));
                tabPanels.forEach(p => p.classList.remove('active'));

                btn.classList.add('active');
                document.getElementById(`tab-${tabId}`).classList.add('active');
            });
        });
    },

    setupFormHandlers() {
        // Botones de guardar en cada tab
        document.querySelectorAll('.tab-panel .btn-primary').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.saveSettings();
            });
        });

        // Botones de cancelar
        document.querySelectorAll('.tab-panel .btn-secondary').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.loadSettings();
                this.showNotification('Cambios descartados', 'info');
            });
        });

        // Cambiar contraseña
        const changePasswordBtn = document.getElementById('changePasswordBtn');
        if (changePasswordBtn) {
            changePasswordBtn.addEventListener('click', () => {
                const current = document.getElementById('currentPassword').value;
                const newPass = document.getElementById('newPassword').value;
                const confirm = document.getElementById('confirmPassword').value;

                if (!current || !newPass || !confirm) {
                    this.showNotification('Completa todos los campos', 'error');
                    return;
                }

                if (newPass !== confirm) {
                    this.showNotification('Las contraseñas no coinciden', 'error');
                    return;
                }

                if (newPass.length < 8) {
                    this.showNotification('La contraseña debe tener al menos 8 caracteres', 'error');
                    return;
                }

                this.showNotification('Contraseña actualizada exitosamente', 'success');
                document.getElementById('currentPassword').value = '';
                document.getElementById('newPassword').value = '';
                document.getElementById('confirmPassword').value = '';
            });
        }

        // Cerrar sesión en otros dispositivos
        document.querySelectorAll('.session-close-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const sessionItem = btn.closest('.session-item');
                sessionItem.style.opacity = '0.5';
                btn.textContent = 'Cerrada';
                btn.disabled = true;
                this.showNotification('Sesión cerrada', 'success');
            });
        });

        // Conectar integraciones
        document.querySelectorAll('.integration-connect-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const integrationName = btn.closest('.integration-card').querySelector('h4').textContent;
                btn.textContent = 'Conectado ✓';
                btn.classList.remove('btn-secondary');
                btn.classList.add('btn-success');
                this.showNotification(`${integrationName} conectado exitosamente`, 'success');
            });
        });
    },

    setupToggleHandlers() {
        document.querySelectorAll('.toggle-switch input').forEach(toggle => {
            toggle.addEventListener('change', (e) => {
                const settingName = e.target.closest('.setting-item').querySelector('h4').textContent;
                const status = e.target.checked ? 'activada' : 'desactivada';
                this.showNotification(`${settingName} ${status}`, 'info');
            });
        });
    },

    showNotification(message, type = 'info') {
        // Crear notificación
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
            <span class="notification-message">${message}</span>
        `;

        document.body.appendChild(notification);

        // Animar entrada
        setTimeout(() => notification.classList.add('show'), 10);

        // Remover después de 3 segundos
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

document.addEventListener('DOMContentLoaded', () => Settings.init());
