// ============================================================
// frontend/js/appointments.js - Gestión de Citas
// ============================================================

document.addEventListener('DOMContentLoaded', async function() {
    if (!Auth.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    await Promise.all([loadAppointments(), loadStats()]);
    setupEventListeners();
    console.log('✅ Página de Citas cargada');
});

async function loadAppointments(fecha, estado) {
    fecha = fecha || '';
    estado = estado || '';
    try {
        const response = await API.appointments.list(fecha, estado);
        renderAppointmentsList(response.appointments || []);
    } catch (error) {
        console.error('Error cargando citas:', error);
        showToast('No se pudieron cargar las citas', 'error');
    }
}

async function loadStats() {
    try {
        const stats = await API.appointments.stats();
        updateStatsCards(stats);
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

function updateStatsCards(stats) {
    const statToday = document.getElementById('statToday');
    const statPending = document.getElementById('statPending');
    const statRevenue = document.getElementById('statRevenue');
    if (statToday) statToday.textContent = stats.total_citas_hoy || 0;
    if (statPending) statPending.textContent = stats.pendientes || 0;
    if (statRevenue) statRevenue.textContent = '$' + (stats.ingresos_hoy ? stats.ingresos_hoy.toFixed(2) : '0.00');
}

async function loadPatientsDropdown() {
    try {
        const response = await API.patients.list();
        const select = document.getElementById('appointmentPatient');
        if (select && response.patients) {
            select.innerHTML = '<option value="">Seleccionar paciente...</option>' +
                response.patients.map(function(p) {
                    return '<option value="' + p.id + '">' + p.nombre + ' ' + p.apellido + '</option>';
                }).join('');
        }
    } catch (error) {
        console.error('Error cargando pacientes:', error);
    }
}

function renderAppointmentsList(appointments) {
    const container = document.getElementById('appointmentsList');
    if (!container) return;

    if (appointments.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 2rem; color: #6b7280;">No hay citas programadas</div>';
        return;
    }

    const statusConfig = {
        confirmed: { label: 'Confirmada', color: 'success' },
        pending: { label: 'Pendiente', color: 'warning' },
        cancelled: { label: 'Cancelada', color: 'danger' },
        completed: { label: 'Completada', color: 'secondary' }
    };

    container.innerHTML = appointments.map(function(apt) {
        const status = statusConfig[apt.estado] || statusConfig.pending;
        return '<div class="appointment-item">' +
            '<div class="appointment-time"><div class="time-badge">' + (apt.time || apt.hora_inicio) + '</div></div>' +
            '<div class="appointment-content"><h4>' + (apt.patient || apt.patient_name) + '</h4><p>' + apt.service + '</p><p class="appointment-therapist">👨‍⚕️ ' + (apt.therapist || 'Sin asignar') + '</p></div>' +
            '<div class="appointment-status"><span class="badge badge-' + status.color + '">' + status.label + '</span></div>' +
            '<div class="appointment-actions"><button class="btn-icon-small" title="Editar" onclick="editAppointment(\'' + apt.id + '\')">✏️</button><button class="btn-icon-small" title="Cancelar" onclick="deleteAppointment(\'' + apt.id + '\')">🗑️</button></div>' +
        '</div>';
    }).join('');
}

function setupEventListeners() {
    const dateFilter = document.getElementById('filterDate');
    const statusFilter = document.getElementById('filterStatus');

    if (dateFilter || statusFilter) {
        const applyFilters = function() {
            loadAppointments(dateFilter ? dateFilter.value : '', statusFilter ? statusFilter.value : '');
        };
        if (dateFilter) dateFilter.addEventListener('change', applyFilters);
        if (statusFilter) statusFilter.addEventListener('change', applyFilters);
    }

    const modal = document.getElementById('newAppointmentModal');
    const btnNew = document.getElementById('btnNewAppointment');
    const btnCancel = document.getElementById('cancelAppointment');
    const btnSave = document.getElementById('saveAppointment');

    if (btnNew) {
        btnNew.addEventListener('click', async function() {
            await loadPatientsDropdown();
            modal.style.display = 'flex';
        });
    }

    if (btnCancel) {
        btnCancel.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }

    if (btnSave) {
        btnSave.addEventListener('click', async function() {
            try {
                const formData = {
                    patient_id: document.getElementById('appointmentPatient').value,
                    service: document.getElementById('appointmentService').value,
                    fecha: document.getElementById('appointmentDate').value,
                    time: document.getElementById('appointmentTime').value,
                    therapist: document.getElementById('appointmentTherapist').value,
                    notas: document.getElementById('appointmentNotes').value
                };

                await API.appointments.create(formData);
                showToast('Cita agendada exitosamente', 'success');
                modal.style.display = 'none';
                loadAppointments();
                loadStats();
            } catch (error) {
                showToast('Error al crear cita: ' + error.message, 'error');
            }
        });
    }

    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
}

window.editAppointment = function(id) {
    showToast('Función de editar en desarrollo', 'info');
};

window.deleteAppointment = async function(id) {
    if (confirm('¿Estás seguro de cancelar esta cita?')) {
        try {
            await API.appointments.delete(id);
            showToast('Cita cancelada', 'success');
            loadAppointments();
            loadStats();
        } catch (error) {
            showToast('Error al cancelar: ' + error.message, 'error');
        }
    }
};

function showToast(message, type) {
    type = type || 'info';
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = 'position: fixed; top: 20px; right: 20px; padding: 1rem; background: ' + (type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6') + '; color: white; border-radius: 0.5rem; z-index: 10000;';
    document.body.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}
