// ============================================================
// frontend/js/patients.js - Gestión de Pacientes
// ============================================================

document.addEventListener('DOMContentLoaded', async function() {
    if (!Auth.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    await loadPatients();
    setupEventListeners();
    console.log('✅ Página de Pacientes cargada');
});

async function loadPatients(search) {
    search = search || '';
    try {
        const response = await API.patients.list(search);
        renderPatients(response.patients || []);
        updateStats(response.patients || []);
    } catch (error) {
        console.error('Error cargando pacientes:', error);
        showToast('No se pudieron cargar los pacientes', 'error');
    }
}

function renderPatients(patients) {
    const tbody = document.getElementById('patientsTableBody');
    if (!tbody) return;

    if (patients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem;">No hay pacientes registrados</td></tr>';
        return;
    }

    tbody.innerHTML = patients.map(function(patient) {
        return '<tr>' +
            '<td><div class="patient-cell"><div class="patient-avatar">' + patient.nombre[0] + patient.apellido[0] + '</div><div><div class="patient-name">' + patient.nombre + ' ' + patient.apellido + '</div><div class="patient-email">' + (patient.email || 'Sin email') + '</div></div></div></td>' +
            '<td><div>📞 ' + patient.telefono + '</div></td>' +
            '<td><span>' + (patient.ultima_cita || 'N/A') + '</span></td>' +
            '<td><span class="badge badge-secondary">' + (patient.total_citas || 0) + ' citas</span></td>' +
            '<td><span class="status-badge ' + (patient.activo ? 'active' : 'inactive') + '">' + (patient.activo ? '✓ Activo' : '✕ Inactivo') + '</span></td>' +
            '<td><div class="actions"><button class="btn-icon" title="Editar" onclick="editPatient(\'' + patient.id + '\')">✏️</button><button class="btn-icon" title="Eliminar" onclick="deletePatient(\'' + patient.id + '\')">🗑️</button></div></td>' +
        '</tr>';
    }).join('');
}

function updateStats(patients) {
    const total = patients.length;
    const activos = patients.filter(function(p) { return p.activo; }).length;
    const statTotal = document.getElementById('statTotal');
    const statActive = document.getElementById('statActive');
    if (statTotal) statTotal.textContent = total;
    if (statActive) statActive.textContent = activos;
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchPatients');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            loadPatients(e.target.value);
        });
    }

    const modal = document.getElementById('newPatientModal');
    const btnNew = document.getElementById('btnNewPatient');
    const btnCancel = document.getElementById('cancelPatient');
    const btnSave = document.getElementById('savePatient');

    if (btnNew) {
        btnNew.addEventListener('click', function() {
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
                    nombre: document.getElementById('patientNombre').value,
                    apellido: document.getElementById('patientApellido').value,
                    email: document.getElementById('patientEmail').value,
                    telefono: document.getElementById('patientPhone').value,
                    fecha_nacimiento: document.getElementById('patientBirthdate').value,
                    genero: document.getElementById('patientGender').value,
                    direccion: document.getElementById('patientAddress').value,
                    notas_medicas: document.getElementById('patientNotes').value
                };

                await API.patients.create(formData);
                showToast('Paciente creado exitosamente', 'success');
                modal.style.display = 'none';
                loadPatients();
            } catch (error) {
                showToast('Error al crear paciente: ' + error.message, 'error');
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

window.editPatient = function(id) {
    showToast('Función de editar en desarrollo', 'info');
};

window.deletePatient = async function(id) {
    if (confirm('¿Estás seguro de eliminar este paciente?')) {
        try {
            await API.patients.delete(id);
            showToast('Paciente eliminado', 'success');
            loadPatients();
        } catch (error) {
            showToast('Error al eliminar: ' + error.message, 'error');
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
