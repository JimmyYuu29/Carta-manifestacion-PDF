/**
 * Carta de Manifestacion Generator - Frontend JavaScript
 * API Client and UI Logic
 */

// ==================== Global State ====================
let currentUser = null;
let authToken = null;

// ==================== API Base URL ====================
const API_BASE = '';

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Load available accounts
    await loadAvailableAccounts();

    // Check for saved session
    const savedToken = localStorage.getItem('authToken');
    if (savedToken) {
        authToken = savedToken;
        try {
            await validateSession();
        } catch (e) {
            // Session expired, clear it
            localStorage.removeItem('authToken');
            authToken = null;
        }
    }

    // Initialize form handlers
    initializeFormHandlers();

    // Set default dates
    setDefaultDates();

    // Initialize directors fields
    updateDirectorsFields();

    // Load system status
    loadSystemStatus();
}

// ==================== Authentication ====================
async function loadAvailableAccounts() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/accounts`);
        const data = await response.json();

        const accountsList = document.getElementById('normal-accounts-list');
        if (accountsList && data.normal_accounts) {
            accountsList.innerHTML = data.normal_accounts
                .map(acc => `<div>${acc}</div>`)
                .join('');
        }
    } catch (e) {
        console.error('Error loading accounts:', e);
    }
}

async function validateSession() {
    const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: {
            'Authorization': `Bearer ${authToken}`
        }
    });

    if (response.ok) {
        currentUser = await response.json();
        showAuthenticatedUI();
    } else {
        throw new Error('Session invalid');
    }
}

async function loginNormal() {
    const username = document.getElementById('normal-username').value.trim();

    if (!username) {
        showToast('Por favor ingrese su usuario.', 'warning');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                account_type: 'normal'
            })
        });

        const data = await response.json();

        if (data.success) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            showToast(`Bienvenido/a, ${data.user.display_name}!`, 'success');
            showAuthenticatedUI();
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Error de conexion. Por favor intente de nuevo.', 'error');
    }

    hideLoading();
}

async function loginPro() {
    const username = document.getElementById('pro-username').value.trim();
    const password = document.getElementById('pro-password').value;

    if (!username || !password) {
        showToast('Por favor ingrese usuario y contrasena.', 'warning');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                password: password,
                account_type: 'pro'
            })
        });

        const data = await response.json();

        if (data.success) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            showToast(`Bienvenido/a, ${data.user.display_name}!`, 'success');
            showAuthenticatedUI();
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Error de conexion. Por favor intente de nuevo.', 'error');
    }

    hideLoading();
}

async function logout() {
    showLoading();

    try {
        await fetch(`${API_BASE}/api/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
    } catch (e) {
        // Ignore logout errors
    }

    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');

    showUnauthenticatedUI();
    showToast('Sesion cerrada correctamente.', 'info');

    hideLoading();
}

// ==================== UI State Management ====================
function showAuthenticatedUI() {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('user-section').style.display = 'block';
    document.getElementById('welcome-screen').style.display = 'none';
    document.getElementById('main-form').style.display = 'block';

    // Update user info in sidebar
    document.getElementById('user-display-name').textContent = currentUser.display_name;
    document.getElementById('user-type').textContent = currentUser.account_type === 'pro' ? 'Pro' : 'Normal';
    document.getElementById('user-email').textContent = currentUser.email || '-';

    // Update permissions
    const permissionsList = document.getElementById('permissions-list');
    const permLabels = {
        can_download_pdf: 'Descargar PDF',
        can_download_word: 'Descargar Word',
        can_view_hash: 'Ver Hash',
        can_export_metadata: 'Exportar Metadatos',
        can_import_metadata: 'Importar Metadatos'
    };

    permissionsList.innerHTML = Object.entries(permLabels)
        .map(([key, label]) => {
            const hasPermission = currentUser.permissions[key];
            const icon = hasPermission ? '&#10004;' : '&#10008;';
            const color = hasPermission ? 'green' : 'red';
            return `<div class="permission-item"><span style="color: ${color}">${icon}</span> ${label}</div>`;
        })
        .join('');
}

function showUnauthenticatedUI() {
    document.getElementById('login-section').style.display = 'block';
    document.getElementById('user-section').style.display = 'none';
    document.getElementById('welcome-screen').style.display = 'block';
    document.getElementById('main-form').style.display = 'none';
}

function toggleAccountType() {
    const accountType = document.querySelector('input[name="account_type"]:checked').value;

    if (accountType === 'normal') {
        document.getElementById('normal-login').style.display = 'block';
        document.getElementById('pro-login').style.display = 'none';
        document.getElementById('features-normal').style.display = 'block';
        document.getElementById('features-pro').style.display = 'none';
    } else {
        document.getElementById('normal-login').style.display = 'none';
        document.getElementById('pro-login').style.display = 'block';
        document.getElementById('features-normal').style.display = 'none';
        document.getElementById('features-pro').style.display = 'block';
    }
}

function toggleConditionalSection(sectionId) {
    const checkbox = document.getElementById(sectionId);
    const details = document.getElementById(`${sectionId}-details`);

    if (details) {
        details.style.display = checkbox.checked ? 'block' : 'none';
    }
}

// ==================== System Status ====================
async function loadSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/system/status`);
        const data = await response.json();

        const statusDiv = document.getElementById('system-status');
        if (statusDiv) {
            if (data.pdf_conversion_available) {
                statusDiv.innerHTML = '<span style="color: green">&#10004; Conversion PDF disponible</span>';
            } else {
                statusDiv.innerHTML = '<span style="color: orange">&#9888; Conversion PDF no disponible</span>';
            }
        }
    } catch (e) {
        console.error('Error loading system status:', e);
    }
}

// ==================== Form Handling ====================
function initializeFormHandlers() {
    const form = document.getElementById('document-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
}

function setDefaultDates() {
    const today = new Date().toISOString().split('T')[0];
    const dateFields = ['Fecha_de_hoy', 'Fecha_encargo', 'FF_Ejecicio', 'Fecha_cierre'];

    dateFields.forEach(field => {
        const input = document.getElementById(field);
        if (input && !input.value) {
            input.value = today;
        }
    });
}

function updateDirectorsFields() {
    const numDirectors = parseInt(document.getElementById('num_directivos').value) || 0;
    const container = document.getElementById('directors-container');

    container.innerHTML = '';

    for (let i = 0; i < numDirectors; i++) {
        const row = document.createElement('div');
        row.className = 'director-row';
        row.innerHTML = `
            <div class="form-group">
                <label for="dir_nombre_${i}">Nombre completo ${i + 1}</label>
                <input type="text" id="dir_nombre_${i}" name="dir_nombre_${i}">
            </div>
            <div class="form-group">
                <label for="dir_cargo_${i}">Cargo ${i + 1}</label>
                <input type="text" id="dir_cargo_${i}" name="dir_cargo_${i}">
            </div>
        `;
        container.appendChild(row);
    }
}

function formatDateForAPI(dateStr) {
    if (!dateStr) return null;

    const date = new Date(dateStr);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();

    return `${day}/${month}/${year}`;
}

function collectFormData() {
    const form = document.getElementById('document-form');
    const formData = new FormData(form);

    const data = {};

    // Text fields
    const textFields = [
        'Direccion_Oficina', 'CP', 'Ciudad_Oficina', 'Nombre_Cliente',
        'Lista_Abogados', 'anexo_partes', 'anexo_proyecciones', 'organo',
        'Anio_incorreccion', 'Epigrafe', 'detalle_limitacion',
        'nombre_experto', 'experto_valoracion',
        'nombre_unidad', 'nombre_mayor_sociedad', 'localizacion_mer',
        'ejercicio_recuperacion_inicio', 'ejercicio_recuperacion_fin',
        'detalle_operacion_fiscal',
        'Nombre_Firma', 'Cargo_Firma'
    ];

    textFields.forEach(field => {
        const input = document.getElementById(field);
        if (input) {
            data[field] = input.value;
        }
    });

    // Date fields
    const dateFields = ['Fecha_de_hoy', 'Fecha_encargo', 'FF_Ejecicio', 'Fecha_cierre'];
    dateFields.forEach(field => {
        const input = document.getElementById(field);
        if (input && input.value) {
            data[field] = formatDateForAPI(input.value);
        }
    });

    // Checkbox fields (convert to 'si'/'no')
    const checkboxFields = [
        'comision', 'junta', 'comite', 'incorreccion', 'dudas', 'rent',
        'A_coste', 'experto', 'unidad_decision', 'activo_impuesto',
        'operacion_fiscal', 'compromiso', 'gestion', 'limitacion_alcance'
    ];

    checkboxFields.forEach(field => {
        const checkbox = document.getElementById(field);
        if (checkbox) {
            data[field] = checkbox.checked ? 'si' : 'no';
        }
    });

    // Directors list
    const numDirectors = parseInt(document.getElementById('num_directivos').value) || 0;
    const directors = [];

    for (let i = 0; i < numDirectors; i++) {
        const nombre = document.getElementById(`dir_nombre_${i}`)?.value;
        const cargo = document.getElementById(`dir_cargo_${i}`)?.value;

        if (nombre && cargo) {
            directors.push({ nombre, cargo });
        }
    }

    data.lista_alto_directores = directors;

    return data;
}

async function handleFormSubmit(e) {
    e.preventDefault();

    // Validate required fields
    const requiredFields = ['Direccion_Oficina', 'CP', 'Ciudad_Oficina', 'Nombre_Cliente'];
    const missingFields = requiredFields.filter(field => {
        const input = document.getElementById(field);
        return !input || !input.value.trim();
    });

    if (missingFields.length > 0) {
        showToast(`Por favor completa los campos obligatorios: ${missingFields.join(', ')}`, 'error');
        return;
    }

    showLoading();

    try {
        const formData = collectFormData();

        const response = await fetch(`${API_BASE}/api/documents/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            showToast('Carta generada exitosamente!', 'success');
            displayGenerationResult(data);
        } else {
            showToast(`Error: ${data.message}`, 'error');
            displayGenerationError(data);
        }
    } catch (e) {
        showToast('Error de conexion. Por favor intente de nuevo.', 'error');
        console.error('Form submission error:', e);
    }

    hideLoading();
}

// ==================== Results Display ====================
function displayGenerationResult(data) {
    const resultsSection = document.getElementById('results-section');
    const resultMessage = document.getElementById('result-message');
    const hashInfo = document.getElementById('hash-info');
    const downloadSection = document.getElementById('download-section');

    resultsSection.style.display = 'block';

    // Success message
    resultMessage.innerHTML = `<div class="success-box">${data.message}</div>`;

    // Hash info
    if (data.hash_info) {
        hashInfo.style.display = 'block';

        document.getElementById('trace-id').textContent = data.trace_id;
        document.getElementById('hash-code').textContent = data.hash_info.hash_code;

        // Full hash details
        document.getElementById('hash-full-details').textContent = `
Codigo de Hash: ${data.hash_info.hash_code}
Algoritmo: ${data.hash_info.algorithm}
Fecha de Creacion: ${data.hash_info.creation_timestamp}
Tamano del Archivo: ${data.hash_info.file_size.toLocaleString()} bytes
Usuario: ${data.hash_info.user_id || '-'}
Cliente: ${data.hash_info.client_name || '-'}
Hash de Contenido: ${data.hash_info.content_hash}
Hash Combinado: ${data.hash_info.combined_hash}
        `.trim();

        // Generation info
        document.getElementById('generation-info').innerHTML = `
            Tiempo de generacion: ${data.duration_ms}ms | Usuario: ${currentUser.display_name}
        `;
    }

    // Download buttons
    if (data.download_links) {
        downloadSection.style.display = 'block';

        const buttonsContainer = document.getElementById('download-buttons');
        buttonsContainer.innerHTML = '';

        if (data.download_links.pdf) {
            const pdfBtn = document.createElement('a');
            pdfBtn.href = data.download_links.pdf;
            pdfBtn.className = 'download-btn download-btn-pdf';
            pdfBtn.innerHTML = '&#128196; Descargar PDF';
            pdfBtn.onclick = (e) => handleDownload(e, data.download_links.pdf, 'pdf');
            buttonsContainer.appendChild(pdfBtn);
        }

        if (data.download_links.docx && currentUser.permissions.can_download_word) {
            const docxBtn = document.createElement('a');
            docxBtn.href = data.download_links.docx;
            docxBtn.className = 'download-btn download-btn-word';
            docxBtn.innerHTML = '&#128221; Descargar Word';
            docxBtn.onclick = (e) => handleDownload(e, data.download_links.docx, 'docx');
            buttonsContainer.appendChild(docxBtn);
        }

        if (!currentUser.permissions.can_download_word) {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'info-text';
            infoDiv.style.marginTop = '0.5rem';
            infoDiv.textContent = 'Los usuarios Pro pueden descargar tambien en formato Word editable.';
            buttonsContainer.appendChild(infoDiv);
        }
    }

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function displayGenerationError(data) {
    const resultsSection = document.getElementById('results-section');
    const resultMessage = document.getElementById('result-message');

    resultsSection.style.display = 'block';
    document.getElementById('hash-info').style.display = 'none';
    document.getElementById('download-section').style.display = 'none';

    let errorHtml = `<div class="error-box">${data.message}</div>`;

    if (data.validation_errors && data.validation_errors.length > 0) {
        errorHtml += '<div class="warning-box"><strong>Errores de validacion:</strong><ul>';
        data.validation_errors.forEach(err => {
            errorHtml += `<li>${err}</li>`;
        });
        errorHtml += '</ul></div>';
    }

    if (data.trace_id) {
        errorHtml += `<p class="info-text">Codigo de traza: ${data.trace_id}</p>`;
    }

    resultMessage.innerHTML = errorHtml;
}

async function handleDownload(e, url, format) {
    e.preventDefault();

    showLoading();

    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al descargar');
        }

        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `documento.${format}`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?(.+)"?/);
            if (match) {
                filename = match[1];
            }
        }

        // Download the file
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        showToast('Archivo descargado exitosamente.', 'success');
    } catch (e) {
        showToast(`Error al descargar: ${e.message}`, 'error');
    }

    hideLoading();
}

// ==================== UI Utilities ====================
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 5000);
}
