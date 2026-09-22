// ============================================================
// frontend/js/app.js - Lógica específica del Dashboard
// ============================================================

const App = {
    init() {
        if (!Auth.isAuthenticated()) {
            window.location.href = 'login.html';
            return;
        }
        this.showCurrentDate();
        this.renderWeeklyChart();
        this.renderRevenueChart();
        console.log('✅ SPA Management System inicializado');
    },

    showCurrentDate() {
        const dateEl = document.getElementById('currentDate');
        if (dateEl) {
            const now = new Date();
            dateEl.textContent = now.toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        }
    },

    renderWeeklyChart() {
        const chartContainer = document.getElementById('weeklyChart');
        if (!chartContainer) return;
        const data = [{ day: 'Lun', value: 8 }, { day: 'Mar', value: 12 }, { day: 'Mié', value: 10 }, { day: 'Jue', value: 15 }, { day: 'Vie', value: 9 }, { day: 'Sáb', value: 7 }, { day: 'Dom', value: 3 }];
        const maxValue = Math.max(...data.map(d => d.value));
        chartContainer.innerHTML = data.map(item => {
            const height = (item.value / maxValue) * 100;
            return `<div class="chart-bar-item"><div class="chart-bar" style="height: ${height}%" title="${item.value} citas"></div><span class="chart-bar-label">${item.day}</span></div>`;
        }).join('');
    },

    renderRevenueChart() {
        const chartContainer = document.getElementById('revenueChart');
        if (!chartContainer) return;
        const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        const values = [1200, 1500, 1400, 1800, 2100, 1900, 2400, 2300, 2800, 2597, 2700, 2900];
        const max = Math.max(...values), min = Math.min(...values), range = max - min;
        const points = values.map((v, i) => `${5 + (i / 11) * 90},${55 - ((v - min) / range) * 50}`).join(' ');
        const area = `5,55 ${points} 95,55`;
        
        chartContainer.innerHTML = `
            <svg viewBox="0 0 100 60" preserveAspectRatio="none" style="width: 100%; height: 200px;">
                <defs><linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#10b981" stop-opacity="0.3"/><stop offset="100%" stop-color="#10b981" stop-opacity="0.05"/></linearGradient></defs>
                <polygon fill="url(#revGrad)" points="${area}"/>
                <polyline fill="none" stroke="#10b981" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" points="${points}"/>
            </svg>
            <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: #666;">${months.map(m => `<span>${m}</span>`).join('')}</div>
        `;
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());
