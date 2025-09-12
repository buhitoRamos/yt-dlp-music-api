/* Music Downloader API - Frontend JavaScript */

// Configuración de la API
const API_BASE = window.location.origin;
let currentJobId = null;
let statusInterval = null;
let localDirectoryHandle = null; // File System Access API directory handle
let lastStatusCache = null;

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
    // Modal cookies
    const openCookies = document.getElementById('openCookies');
    const modal = document.getElementById('cookiesModal');
    const closeCookies = document.getElementById('closeCookies');
    const uploadBtn = document.getElementById('uploadCookiesBtn');
    const clearBtn = document.getElementById('clearCookiesBtn');
    const cookieArea = document.getElementById('cookieText');
    const cookiesStatus = document.getElementById('cookiesStatus');
    if (openCookies && modal) {
        openCookies.addEventListener('click', ()=> { modal.style.display='flex'; });
    }
    if (closeCookies && modal) {
        closeCookies.addEventListener('click', ()=> { modal.style.display='none'; });
    }
    if (modal) {
        modal.addEventListener('click', (e)=> { if (e.target === modal) modal.style.display='none'; });
    }
    // Restaurar de localStorage si existe
    try {
        const saved = localStorage.getItem('yt_cookies_text');
        if (saved && cookieArea) cookieArea.value = saved;
    } catch(e){}
    if (uploadBtn && cookieArea) {
        uploadBtn.addEventListener('click', async () => {
            const txt = cookieArea.value.trim();
            if (!txt) { cookiesStatus.textContent = 'Vacío'; cookiesStatus.className='cookies-status err'; return; }
            cookiesStatus.textContent = 'Subiendo...'; cookiesStatus.className='cookies-status';
            try {
                const resp = await fetch(`${API_BASE}/upload-cookies`, {
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({cookies_text: txt})
                });
                const data = await resp.json();
                if (resp.ok) {
                    cookiesStatus.textContent = '✅ Cargadas'; cookiesStatus.className='cookies-status ok';
                    try { localStorage.setItem('yt_cookies_text', txt); } catch(e){}
                    showTemporaryMessage('🍪 Cookies cargadas');
                } else {
                    cookiesStatus.textContent = '❌ ' + (data.error || 'Error'); cookiesStatus.className='cookies-status err';
                }
            } catch(err) {
                cookiesStatus.textContent = '❌ Conexión'; cookiesStatus.className='cookies-status err';
            }
        });
    }

    // Botón para elegir carpeta local real (File System Access API)
    const pickBtn = document.getElementById('pickLocalDirBtn');
    if (pickBtn) {
        pickBtn.addEventListener('click', async ()=>{
            if (!('showDirectoryPicker' in window)) {
                showTemporaryMessage('⚠️ Tu navegador no soporta File System Access API');
                return;
            }
            try {
                localDirectoryHandle = await window.showDirectoryPicker();
                showTemporaryMessage('📁 Carpeta local autorizada');
                pickBtn.textContent = '📁 Carpeta autorizada';
                pickBtn.disabled = true;
            } catch(e) {
                showTemporaryMessage('❌ Cancelado');
            }
        });
    }

    // Guardar localmente
    const saveLocallyBtn = document.getElementById('saveLocallyBtn');
    if (saveLocallyBtn) {
        saveLocallyBtn.addEventListener('click', async ()=>{
            if (!lastStatusCache || !lastStatusCache.download_urls) {
                showTemporaryMessage('No hay archivos para guardar');
                return;
            }
            if (!localDirectoryHandle) {
                showTemporaryMessage('Elige primero una carpeta local');
                return;
            }
            const statusLabel = document.getElementById('localSaveStatus');
            statusLabel.textContent = 'Guardando...';
            let ok = 0; let fail = 0;
            for (let i=0;i<lastStatusCache.download_urls.length;i++) {
                const url = lastStatusCache.download_urls[i];
                try {
                    const resp = await fetch(url);
                    if (!resp.ok) throw new Error('HTTP '+resp.status);
                    const blob = await resp.blob();
                    const serverPath = (lastStatusCache.files && lastStatusCache.files[i]) || `file_${i}`;
                    const baseName = serverPath.split('/').pop();
                    const fileHandle = await localDirectoryHandle.getFileHandle(baseName, {create:true});
                    const writable = await fileHandle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    ok++;
                } catch(err) {
                    console.error('Save error', err);
                    fail++;
                }
            }
            statusLabel.textContent = `Guardados: ${ok}, Fallidos: ${fail}`;
        });
    }

    // Limpiar remoto
    const cleanupBtn = document.getElementById('cleanupRemoteBtn');
    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', async ()=>{
            if (!currentJobId) return;
            try {
                const r = await fetch(`${API_BASE}/cleanup/${currentJobId}`, {method:'POST'});
                const d = await r.json();
                showTemporaryMessage('🧹 Limpieza remota realizada');
                document.getElementById('localSaveStatus').textContent = 'Servidor limpio';
                // Forzar refresco de estado para ocultar botones
                setTimeout(checkStatus, 800);
            } catch(e) {
                showTemporaryMessage('Error limpiando remoto');
            }
        });
    }
    if (clearBtn && cookieArea) {
        clearBtn.addEventListener('click', () => {
            cookieArea.value='';
            cookiesStatus.textContent='';
            cookiesStatus.className='cookies-status';
            try { localStorage.removeItem('yt_cookies_text'); } catch(e){}
        });
    }
    
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
        // Ajustes de formato/calidad: si formato es mp4 ignorar quality
        if (data.format === 'mp4') {
            delete data.quality; // backend puede usar mejor calidad por defecto para video
        }
        // Añadir flags avanzados
    const fl = document.getElementById('force_local'); // Puede no existir tras simplificación
    if (fl) data.force_local = fl.checked ? '1' : '0';
        
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

// Toggle de calidad según formato
document.addEventListener('change', function(e){
    if (e.target && e.target.id === 'format') {
        const fmt = e.target.value;
        const wrapper = document.getElementById('qualityWrapper');
        if (!wrapper) return;
        if (fmt === 'mp4') {
            wrapper.style.opacity = '0.35';
            wrapper.style.pointerEvents = 'none';
            const q = document.getElementById('quality');
            if (q) q.setAttribute('disabled','disabled');
        } else {
            wrapper.style.opacity = '1';
            wrapper.style.pointerEvents = 'auto';
            const q = document.getElementById('quality');
            if (q) q.removeAttribute('disabled');
        }
    }
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
    lastStatusCache = status; // cache
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
                // Mostrar acciones locales si hay soporte API y archivos
                const act = document.getElementById('localSaveActions');
                if (act) {
                    act.style.display = 'block';
                }
            }
            // Si el navegador soporta FS API y hay URLs, intentar auto-guardar si ya se autorizó
            if (status.download_urls && localDirectoryHandle) {
                autoSaveAndCleanup(status).catch(()=>{});
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
        if (status.prefetch_client) lines.push(`🛰 Prefetch client: <code>${status.prefetch_client}</code>`);
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
    if (status.cookie_stage) lines.push(`🍪 Etapa cookies: <code>${status.cookie_stage}</code>`);
    if (status.bot_trigger_attempt) lines.push(`🚨 Bot detectado en intento ${status.bot_trigger_attempt}`);
    if (status.auto_cookies_unavailable) lines.push('🚫 Perfiles navegador no disponibles (hosting)');
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

async function autoSaveAndCleanup(status) {
    try {
        const urls = status.download_urls || [];
        if (!urls.length) return;
        let saved = 0;
        for (let i=0;i<urls.length;i++) {
            const u = urls[i];
            const resp = await fetch(u);
            if (!resp.ok) continue;
            const blob = await resp.blob();
            const serverPath = (status.files && status.files[i]) || `file_${i}`;
            const baseName = serverPath.split('/').pop();
            const fileHandle = await localDirectoryHandle.getFileHandle(baseName, {create:true});
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();
            saved++;
        }
        showTemporaryMessage(`💾 Auto-guardados ${saved}/${urls.length}`);
    } catch(e) {
        console.warn('Auto save failed', e);
    }
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

