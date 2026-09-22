// ============================================================
// frontend/js/documentation.js - Página de Documentación
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    setupTabs();
    setupCopyButtons();
    console.log('✅ Página de Documentación cargada');
});

function setupTabs() {
    const tabButtons = document.querySelectorAll('.doc-tab-btn');
    const tabPanels = document.querySelectorAll('.doc-tab-panel');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`tab-${tabId}`).classList.add('active');
        });
    });
}

function setupCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const codeId = btn.dataset.code;
            const codeElement = document.getElementById(`code-${codeId}`);
            
            if (codeElement) {
                const text = codeElement.textContent;
                navigator.clipboard.writeText(text).then(() => {
                    const originalText = btn.textContent;
                    btn.textContent = '✓ Copiado';
                    btn.style.background = '#10b981';
                    btn.style.color = 'white';
                    
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.style.background = '';
                        btn.style.color = '';
                    }, 2000);
                }).catch(err => {
                    console.error('Error al copiar:', err);
                });
            }
        });
    });
}
