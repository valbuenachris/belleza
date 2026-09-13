// ============================================================
// frontend/js/auth.js - Módulo de autenticación
// Maneja login, logout, tokens y estado de sesión
// ============================================================

/**
 * Módulo de autenticación.
 * Gestiona el ciclo de vida de la sesión del usuario.
 */
const Auth = {
    // Claves de localStorage
    KEYS: {
        ACCESS_TOKEN: 'spa_access_token',
        REFRESH_TOKEN: 'spa_refresh_token',
        USER: 'spa_user',
        TENANT: 'spa_tenant',
    },

    /**
     * Inicia sesión con email y contraseña.
     * @param {string} email - Correo electrónico
     * @param {string} password - Contraseña
     * @returns {Promise<Object>} Datos del usuario y tokens
     */
    async login(email, password) {
        const response = await api.post('/auth/login', { email, password }, false);
        
        // Guardar tokens y datos del usuario
        this.setSession(response);
        
        // Disparar evento de login
        this.dispatchEvent('spa:login', { user: response.user, tenant: response.tenant });
        
        return response;
    },

    /**
     * Cierra la sesión del usuario.
     */
    async logout() {
        try {
            await api.post('/auth/logout');
        } catch {
            // Ignorar errores de logout
        }
        
        this.clearSession();
        
        // Disparar evento de logout
        this.dispatchEvent('spa:logout');
        
        // Redirigir a login
        window.location.href = 'login.html';
    },

    /**
     * Verifica si hay una sesión activa.
     * @returns {boolean} True si hay sesión activa
     */
    isAuthenticated() {
        const token = localStorage.getItem(this.KEYS.ACCESS_TOKEN);
        const user = localStorage.getItem(this.KEYS.USER);
        return !!(token && user);
    },

    /**
     * Obtiene el token de acceso actual.
     * @returns {string|null} Token JWT o null
     */
    getToken() {
        return localStorage.getItem(this.KEYS.ACCESS_TOKEN);
    },

    /**
     * Obtiene los datos del usuario actual.
     * @returns {Object|null} Datos del usuario o null
     */
    getCurrentUser() {
        const userStr = localStorage.getItem(this.KEYS.USER);
        if (!userStr) return null;
        
        try {
            return JSON.parse(userStr);
        } catch {
            return null;
        }
    },

    /**
     * Obtiene los datos del tenant actual.
     * @returns {Object|null} Datos del tenant o null
     */
    getTenant() {
        const tenantStr = localStorage.getItem(this.KEYS.TENANT);
        if (!tenantStr) return null;
        
        try {
            return JSON.parse(tenantStr);
        } catch {
            return null;
        }
    },

    /**
     * Verifica si el usuario tiene un rol específico.
     * @param {string} role - Rol a verificar
     * @returns {boolean} True si el usuario tiene el rol
     */
    hasRole(role) {
        const user = this.getCurrentUser();
        return user && user.rol === role;
    },

    /**
     * Verifica si el usuario tiene alguno de los roles especificados.
     * @param {string[]} roles - Lista de roles
     * @returns {boolean} True si tiene alguno
     */
    hasAnyRole(roles) {
        const user = this.getCurrentUser();
        return user && roles.includes(user.rol);
    },

    /**
     * Guarda la sesión completa en localStorage.
     * @param {Object} data - Datos de la respuesta de login
     */
    setSession(data) {
        localStorage.setItem(this.KEYS.ACCESS_TOKEN, data.access_token);
        localStorage.setItem(this.KEYS.REFRESH_TOKEN, data.refresh_token);
        localStorage.setItem(this.KEYS.USER, JSON.stringify(data.user));
        
        if (data.tenant) {
            localStorage.setItem(this.KEYS.TENANT, JSON.stringify(data.tenant));
        }
    },

    /**
     * Limpia todos los datos de sesión.
     */
    clearSession() {
        Object.values(this.KEYS).forEach(key => {
            localStorage.removeItem(key);
        });
    },

    /**
     * Refresca el token de acceso usando el refresh token.
     * @returns {Promise<boolean>} True si se refrescó exitosamente
     */
    async refreshToken() {
        const refreshToken = localStorage.getItem(this.KEYS.REFRESH_TOKEN);
        if (!refreshToken) return false;

        try {
            const response = await api.post('/auth/refresh', { refresh_token: refreshToken }, false);
            this.setSession(response);
            return true;
        } catch {
            this.clearSession();
            return false;
        }
    },

    /**
     * Dispara un evento personalizado.
     * @param {string} eventName - Nombre del evento
     * @param {Object} detail - Datos del evento
     */
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    },

    /**
     * Configura el auto-refresh del token.
     * Verifica periódicamente si el token está cerca de expirar.
     */
    setupAutoRefresh() {
        // Verificar cada 5 minutos
        setInterval(async () => {
            if (!this.isAuthenticated()) return;
            
            const token = this.getToken();
            if (!token) return;
            
            // Decodificar el token para verificar expiración
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                const expiresAt = payload.exp * 1000;
                const now = Date.now();
                const timeLeft = expiresAt - now;
                
                // Si quedan menos de 5 minutos, refrescar
                if (timeLeft < 5 * 60 * 1000 && timeLeft > 0) {
                    await this.refreshToken();
                }
            } catch {
                // Token malformado - limpiar sesión
                this.clearSession();
                window.location.href = 'login.html';
            }
        }, 5 * 60 * 1000);
    },
};

// Configurar auto-refresh al cargar
document.addEventListener('DOMContentLoaded', () => {
    if (Auth.isAuthenticated()) {
        Auth.setupAutoRefresh();
    }
});
