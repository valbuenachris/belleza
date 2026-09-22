// API Client - Minimalist version
var API_BASE = 'http://15.204.10.78:8000/api/v1';

var API = {
    getToken: function() {
        return localStorage.getItem('access_token');
    },
    getHeaders: function() {
        var token = this.getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? 'Bearer ' + token : ''
        };
    },
    request: function(url, method, body) {
        var options = {
            method: method || 'GET',
            headers: this.getHeaders()
        };
        if (body && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(body);
        }
        return fetch(API_BASE + url, options).then(function(response) {
            if (!response.ok) {
                return response.json().then(function(err) { throw new Error(err.detail || 'HTTP ' + response.status); });
            }
            return response.json();
        });
    },
    get: function(url) { return this.request(url, 'GET'); },
    post: function(url, data) { return this.request(url, 'POST', data); },
    put: function(url, data) { return this.request(url, 'PUT', data); },
    'delete': function(url) { return this.request(url, 'DELETE'); },
    patients: {
        list: function(s) { return API.get('/patients' + (s ? '?search=' + encodeURIComponent(s) : '')); },
        create: function(d) { return API.post('/patients', d); },
        'delete': function(id) { return API['delete']('/patients/' + id); }
    },
    appointments: {
        list: function(f, e) { return API.get('/appointments?fecha=' + (f||'') + '&estado=' + (e||'')); },
        create: function(d) { return API.post('/appointments', d); },
        'delete': function(id) { return API['delete']('/appointments/' + id); },
        stats: function() { return API.get('/appointments/stats/summary'); }
    }
};

// Alias para compatibilidad
var api = API;
console.log('API loaded successfully from', API_BASE);
