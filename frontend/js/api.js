// ============================================================
// frontend/js/api.js - Cliente API
// Maneja todas las llamadas al backend FastAPI
// ============================================================

/**
 * Cliente API para comunicarse con el backend.
 * Incluye manejo automático de tokens, refresh, y errores.
 */
class ApiClient {
    constructor() {
        // URL base relativa (Nginx hace de reverse proxy)
        this.baseURL = '/api/v1';
        this.timeout = 30000; // 30 segundos
    }

    /**
     * Obtiene el token de acceso actual desde localStorage.
     */
    getToken() {
        return localStorage.getItem('spa_access_token');
    }

    /**
     * Construye los headers para cada request.
     */
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (includeAuth) {
            const token = this.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        return headers;
    }

    /**
     * Realiza un request HTTP genérico.
     */
    async request(method, endpoint, data = null, includeAuth = true) {
        const url = `${this.baseURL}${endpoint}`;
        const options = {
            method,
            headers: this.getHeaders(includeAuth),
        };

        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }

        // Crear AbortController para timeout
        const controller = new AbortController();
        options.signal = controller.signal;
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(url, options);
            clearTimeout(timeoutId);

            // Manejar respuesta
            const responseData = await response.json().catch(() => null);

            if (!response.ok) {
                // Token expirado - intentar refresh
                if (response.status === 401 && includeAuth) {
                    const refreshed = await this.tryRefreshToken();
                    if (refreshed) {
                        // Reintentar el request original
                        return this.request(method, endpoint, data, includeAuth);
                    } else {
                        // No se pudo refrescar - redirigir a login
                        window.location.href = 'login.html';
                        throw new Error('Sesión expirada. Inicia sesión nuevamente.');
                    }
                }

                // Otros errores
                const errorMessage = responseData?.detail || `Error ${response.status}`;
                throw new Error(errorMessage);
            }

            return responseData;
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new Error('La solicitud tardó demasiado. Intenta de nuevo.');
            }

            if (error.message.includes('Failed to fetch')) {
                throw new Error('No se pudo conectar con el servidor. Verifica tu conexión.');
            }

            throw error;
        }
    }

    /**
     * Intenta refrescar el token de acceso.
     */
    async tryRefreshToken() {
        const refreshToken = localStorage.getItem('spa_refresh_token');
        if (!refreshToken) return false;

        try {
            const response = await fetch(`${this.baseURL}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (!response.ok) return false;

            const data = await response.json();
            localStorage.setItem('spa_access_token', data.access_token);
            localStorage.setItem('spa_refresh_token', data.refresh_token);
            return true;
        } catch {
            return false;
        }
    }

    // ============================================================
    // Métodos HTTP específicos
    // ============================================================

    /**
     * Request GET
     */
    async get(endpoint, includeAuth = true) {
        return this.request('GET', endpoint, null, includeAuth);
    }

    /**
     * Request POST
     */
    async post(endpoint, data = null, includeAuth = true) {
        return this.request('POST', endpoint, data, includeAuth);
    }

    /**
     * Request PUT
     */
    async put(endpoint, data = null, includeAuth = true) {
        return this.request('PUT', endpoint, data, includeAuth);
    }

    /**
     * Request DELETE
     */
    async delete(endpoint, includeAuth = true) {
        return this.request('DELETE', endpoint, null, includeAuth);
    }

    /**
     * Request PATCH
     */
    async patch(endpoint, data = null, includeAuth = true) {
        return this.request('PATCH', endpoint, data, includeAuth);
    }
}

// Instancia global del cliente API
const api = new ApiClient();
