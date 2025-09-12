/* Music Downloader API - Frontend JavaScript */

// Configuración de la API
const API_BASE = window.location.origin;
let currentJobId = null;
let statusInterval = null;

// Función para seleccionar carpeta
async function selectFolder() {
    try {
        // Intentar usar la nueva File System Access API (Chrome 86+)
        if ('showDirectoryPicker' in window) {
            const directoryHandle = await window.showDirectoryPicker();
            const folderPath = directoryHandle.name;
            
            // Construir ruta completa (aproximada)
            const outputField = document.getElementById('output_dir');
            outputField.value = `~/Downloads/${folderPath}`;
            outputField.readOnly = false;
            outputField.style.backgroundColor = '#f0f8ff';
            
            showTemporaryMessage('✅ Carpeta seleccionada con File System API');
            return;
        }
    } catch (error) {
        console.log('File System Access API no disponible o cancelado, usando fallback');
    }
    
    // Fallback: usar el selector tradicional
    const folderInput = document.getElementById('folderInput');
    folderInput.click();
}

// Función para obtener el directorio home del usuario
function getUserHomeDirectory() {
    const isMac = navigator.userAgent.includes('Mac');
    const isWindows = navigator.userAgent.includes('Windows');
    
    if (isMac) {
        // Si estamos en desarrollo local y la URL contiene la ruta del usuario
        if (window.location.href.includes('/Users/')) {
            const userMatch = window.location.href.match(/\/Users\/([^\/]+)/);
            if (userMatch) {
                return `/Users/${userMatch[1]}`;
            }
        }
        // Intentar detectar desde el path actual del archivo
        try {
            // Usar el usuario O002545 que vemos en el contexto
            return '/Users/O002545';
        } catch (e) {
            return '/Users/usuario';
        }
    } else if (isWindows) {
        return 'C:\\Users\\usuario';
    } else {
        // Linux u otros sistemas Unix
        return '/home/usuario';
    }
}

// Función para rutas rápidas
function setQuickPath(path) {
    const outputDir = document.getElementById('output_dir');
    
    // Expandir ~ a la ruta del usuario
    if (path.startsWith('~/')) {
        const homeDir = getUserHomeDirectory();
        path = path.replace('~', homeDir);
    }
    
    outputDir.value = path;
    outputDir.readOnly = false;
    outputDir.style.backgroundColor = '#f0f8ff';
    outputDir.placeholder = 'Edita la ruta si es necesario';
    
    // Enfocar el campo para que el usuario pueda editarlo
    outputDir.focus();
    
    showTemporaryMessage(`✅ Ruta configurada. Puedes editarla si es necesario.`);
}

// Inicializar eventos cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    
    // Manejar selección de carpeta
    document.getElementById('folderInput').addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            // Obtener la ruta de la primera archivo seleccionado
            const file = e.target.files[0];
            let folderPath = file.webkitRelativePath;
            
            // Extraer la ruta de la carpeta (sin el archivo)
            const pathParts = folderPath.split('/');
            
            // Si hay más de una parte, es una carpeta
            if (pathParts.length > 1) {
                pathParts.pop(); // Remover el nombre del archivo
                const selectedPath = pathParts.join('/');
                
                // Intentar construir la ruta completa
                try {
                    const homeDir = getUserHomeDirectory();
                    const fullPath = `${homeDir}/Downloads/${selectedPath}`;
                    document.getElementById('output_dir').value = fullPath;
                } catch (error) {
                    // Fallback simple
                    document.getElementById('output_dir').value = `~/Downloads/${selectedPath}`;
                }
            } else {
                // Si solo hay un nivel, usar el directorio padre
                const fileName = pathParts[0];
                const parentDir = fileName.split('.')[0]; // Usar nombre sin extensión como carpeta
                const homeDir = getUserHomeDirectory();
                document.getElementById('output_dir').value = `${homeDir}/Downloads/${parentDir}_downloads`;
            }
            
            // Hacer el campo editable para ajustes
            const outputField = document.getElementById('output_dir');
            outputField.readOnly = false;
            outputField.style.backgroundColor = '#f0f8ff';
            
            // Mostrar mensaje de éxito
            showTemporaryMessage('✅ Carpeta seleccionada correctamente');
        }
    });

    // Permitir edición manual del campo
    document.getElementById('output_dir').addEventListener('click', function() {
        this.readOnly = false;
        this.placeholder = 'Escribe la ruta completa, ej: /Users/tuusuario/Downloads/musica';
    });

    // Manejar envío del formulario
    document.getElementById('downloadForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const data = Object.fromEntries(formData);
        // Añadir flags avanzados
        const fl = document.getElementById('force_local');
        const fr = document.getElementById('force_remote');
        if (fl) data.force_local = fl.checked ? '1' : '0';
        if (fr) data.force_remote = fr.checked ? '1' : '0';
        
        // Mostrar estado inicial
        showStatus('loading', 'Iniciando descarga...');
        setProgress(0);
        clearFiles();
        hideLog();
        
        // Deshabilitar botón de descarga y mostrar botón de cancelar
        const btn = document.getElementById('downloadBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        btn.disabled = true;
        btn.textContent = '⏳ Descargando...';
        cancelBtn.style.display = 'block';
        
        try {
            const response = await fetch(`${API_BASE}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                currentJobId = result.job_id;
                document.getElementById('jobInfo').textContent = `Job ID: ${currentJobId}`;
                
                // Iniciar polling del estado
                statusInterval = setInterval(checkStatus, 2000);
                // Limpiar panel de estrategia anterior
                const stratBox = document.getElementById('strategyInfo');
                if (stratBox) { stratBox.innerHTML=''; stratBox.style.display='none'; }
            } else {
                showStatus('error', `Error: ${result.error}`);
                resetButton();
            }
            
        } catch (error) {
            showStatus('error', `Error de conexión: ${error.message}`);
            resetButton();
        }
    });

    // Manejar cancelación
    document.getElementById('cancelBtn').addEventListener('click', async function() {
        if (currentJobId) {
            try {
                const response = await fetch(`${API_BASE}/cancel/${currentJobId}`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    showStatus('info', '❌ Descarga cancelada por el usuario');
                    clearInterval(statusInterval);
                    statusInterval = null;
                    currentJobId = null;
                    resetButton();
                } else {
                    showStatus('error', 'No se pudo cancelar la descarga');
                }
            } catch (error) {
                showStatus('error', `Error al cancelar: ${error.message}`);
            }
        }
    });
});

// Verificar estado de descarga
async function checkStatus() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`${API_BASE}/status/${currentJobId}`);
        const status = await response.json();
        
        updateStatusDisplay(status);
        
        if (status.status === 'completado' || status.status === 'error' || status.status === 'cancelado') {
            clearInterval(statusInterval);
            statusInterval = null;
            resetButton();
        }
        
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// Actualizar visualización del estado
function updateStatusDisplay(status) {
    switch (status.status) {
        case 'iniciando':
            showStatus('loading', 'Iniciando descarga...');
            setProgress(0);
            break;
        
        case 'descargando':
            showStatus('loading', 'Descargando archivos...');
            setProgress(50);
            break;
        
        case 'completado':
            showStatus('success', '✅ Descarga completada');
            setProgress(100);
            if (status.files && status.files.length > 0) {
                showFiles(status.files);
            }
            if (status.stdout) {
                showLog(status.stdout);
            }
            break;
        
        case 'error':
            showStatus('error', `❌ Error: ${status.error}`);
            setProgress(0);
            if (status.stdout) {
                showLog(`Error:\n${status.error}\n\nOutput:\n${status.stdout}`);
            }
            break;
        
        case 'cancelado':
            showStatus('info', '❌ Descarga cancelada');
            setProgress(0);
            break;
    }
    // Actualizar panel de estrategia
    try {
        const box = document.getElementById('strategyInfo');
        if (!box) return;
        const lines = [];
        // Campo principal de estado / attempts
        if (status.attempt || status.max_attempts) {
            const att = status.attempt || 0;
            const maxA = status.max_attempts || '?';
            lines.push(`🔁 Intento: <strong>${att}</strong>/<strong>${maxA}</strong>${status.attempts_used !== undefined ? ` (usados:${status.attempts_used})` : ''}`);
        }
        if (status.environment) lines.push(`🌐 Entorno: ${status.environment}`);
        if (status.is_remote_detected !== undefined) lines.push(`🔍 Remoto detectado: ${status.is_remote_detected}`);
        if (status.force_mode) lines.push(`⚙️ Modo forzado: ${status.force_mode}`);
        if (status.anti_bot_level) lines.push(`🛡️ Nivel anti-bot: ${status.anti_bot_level}`);
        if (status.chosen_initial_client) lines.push(`🎯 Cliente inicial: <code>${status.chosen_initial_client}</code>${status.cache_hit ? ' <span class="badge cache-hit">CACHE</span>' : ''}`);
        if (status.prefetch_title) {
            const dur = status.prefetch_duration ? ` (${status.prefetch_duration}s)` : '';
            lines.push(`🕵️ Prefetch: <em>${escapeHtml(status.prefetch_title).substring(0,80)}</em>${dur}`);
        } else if (status.prefetch === false) {
            lines.push('🕵️ Prefetch: <span class="badge off">off</span>');
        }
        if (status.head_check !== undefined) {
            let hcVal = '';
            if (typeof status.head_check === 'object') {
                try { hcVal = JSON.stringify(status.head_check); } catch(e){ hcVal = String(status.head_check); }
            } else {
                hcVal = String(status.head_check);
            }
            lines.push(`� HEAD check: ${hcVal}`);
        }
        if (status.requires_cookies) lines.push(`🍪 Requiere cookies: <span class="badge warn">SI</span>`);
        else if (status.requires_cookies === false) lines.push(`🍪 Requiere cookies: <span class="badge ok">no</span>`);
        if (status.cookies) lines.push(`🍪 ${status.cookies}`);
        if (status.error_type) lines.push(`🚧 Error previo: ${status.error_type}`);
        if (status.info) lines.push(`ℹ️ ${escapeHtml(status.info)}`);
        if (status.user_agent) lines.push(`🧾 UA: ${escapeHtml(status.user_agent.substring(0,120))}...`);
        if (lines.length) {
            box.style.display = 'block';
            box.innerHTML = lines.map(l=>`<div class="line">${l}</div>`).join('');
        }
    } catch(e){ /* noop */ }
}

// Mostrar estado
function showStatus(type, text) {
    const container = document.getElementById('statusContainer');
    const icon = document.getElementById('statusIcon');
    const statusText = document.getElementById('statusText');
    
    container.classList.add('show');
    icon.className = `status-icon ${type}`;
    statusText.textContent = text;
}

// Configurar progreso
function setProgress(percent) {
    document.getElementById('progressFill').style.width = `${percent}%`;
}

// Mostrar archivos descargados
function showFiles(files) {
    const container = document.getElementById('filesContainer');
    const list = document.getElementById('filesList');
    
    list.innerHTML = '';
    files.forEach(file => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.textContent = file.split('/').pop(); // Solo el nombre del archivo
        list.appendChild(item);
    });
    
    container.style.display = 'block';
}

// Limpiar lista de archivos
function clearFiles() {
    document.getElementById('filesContainer').style.display = 'none';
}

// Mostrar log
function showLog(text) {
    const container = document.getElementById('logContainer');
    const output = document.getElementById('logOutput');
    
    output.textContent = text;
    container.style.display = 'block';
}

// Ocultar log
function hideLog() {
    document.getElementById('logContainer').style.display = 'none';
}

// Restablecer botón
function resetButton() {
    const btn = document.getElementById('downloadBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    btn.disabled = false;
    btn.textContent = '🚀 Iniciar Descarga';
    cancelBtn.style.display = 'none';
}

// Cleanup al cerrar la página
window.addEventListener('beforeunload', function() {
    if (statusInterval) {
        clearInterval(statusInterval);
    }
});

// Mostrar mensaje temporal
function showTemporaryMessage(message, duration = 3000) {
    // Crear elemento de mensaje si no existe
    let messageEl = document.getElementById('tempMessage');
    if (!messageEl) {
        messageEl = document.createElement('div');
        messageEl.id = 'tempMessage';
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            z-index: 1000;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        document.body.appendChild(messageEl);
    }
    
    messageEl.textContent = message;
    messageEl.style.transform = 'translateX(0)';
    
    // Ocultar después del tiempo especificado
    setTimeout(() => {
        messageEl.style.transform = 'translateX(100%)';
    }, duration);
}

// Utilidades simples
function escapeHtml(str){
    if (!str) return '';
    return str.replace(/[&<>"]/g, function(c){
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c] || c;
    });
}

