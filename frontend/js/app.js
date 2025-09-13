/* Music Downloader API - Frontend JavaScript */

// Configuración de la API
const API_BASE = window.location.origin;
let currentJobId = null;
let statusInterval = null; // (legacy - mantenido por compatibilidad)
let localDirectoryHandle = null; // File System Access API directory handle
let lastStatusCache = null;
let pollTimer = null;
const POLL_STEPS = [2000, 4000, 6000]; // escalado progresivo 2s -> 4s -> 6s
let pollStepIndex = 0;

// Helper para pedir permisos explícitos si el navegador exige 'user activation'
async function ensureDirectoryWritePermission() {
    if (!localDirectoryHandle) return false;
    try {
        // Algunos navegadores requieren consultar primero
        const opts = {mode:'readwrite'};
        if (localDirectoryHandle.queryPermission) {
            let p = await localDirectoryHandle.queryPermission(opts);
            if (p === 'granted') return true;
            if (p === 'prompt' && localDirectoryHandle.requestPermission) {
                p = await localDirectoryHandle.requestPermission(opts);
                return p === 'granted';
            }
            if (p === 'denied' && localDirectoryHandle.requestPermission) {
                p = await localDirectoryHandle.requestPermission(opts);
                return p === 'granted';
            }
        }
        // Si no existen los métodos asumimos que ya hay permiso tras picker
        return true;
    } catch(e) {
        console.warn('No se pudo confirmar permiso', e);
        return false;
    }
}

// (Simplificado) Eliminadas funciones antiguas de selección manual y manipulación de rutas locales.

// --- Adaptive Polling Backoff ---
// Estrategia: iniciar en 2s; si attempt >=2 o polls >3 pasa a 4s; luego a 6s tras polls >8.
function startAdaptivePolling() {
    clearPolling();
    pollStepIndex = 0;
    scheduleNextPoll(true);
}

function clearPolling() {
    if (statusInterval) { clearInterval(statusInterval); statusInterval = null; }
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
}

function scheduleNextPoll(immediate=false) {
    if (!currentJobId) return;
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    const delay = POLL_STEPS[Math.min(pollStepIndex, POLL_STEPS.length-1)];
    if (immediate) {
        checkStatus();
    } else {
        pollTimer = setTimeout(checkStatus, delay);
    }
}

async function checkStatus() {
    if (!currentJobId) return;
    try {
        const response = await fetch(`${API_BASE}/status/${currentJobId}`);
        const status = await response.json();
        updateStatusDisplay(status);
        const done = ['completado','error','cancelado'].includes(status.status);
        if (done) {
            clearPolling();
            resetButton();
            return;
        }
        // Evolución del backoff
        try {
            const polls = status.status_polls || 0;
            const attempt = status.attempt || 1;
            const nextIndex = pollStepIndex + 1;
            if (nextIndex < POLL_STEPS.length) {
                if (attempt >= 2 || polls >= (pollStepIndex === 0 ? 3 : 8)) {
                    pollStepIndex = nextIndex;
                }
            }
        } catch(e) { /* noop */ }
        scheduleNextPoll();
    } catch (err) {
        console.warn('Status poll error', err);
        scheduleNextPoll();
    }
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

    // Botón para elegir carpeta (solo tras finalizar)
    const pickBtn = document.getElementById('pickLocalDirBtn');
    if (pickBtn) {
        pickBtn.addEventListener('click', async ()=>{
            if (!lastStatusCache || lastStatusCache.status !== 'completado') {
                showTemporaryMessage('Aún no finaliza');
                return;
            }
            if (!('showDirectoryPicker' in window)) {
                showTemporaryMessage('⚠️ Sin File System API: generando enlaces...');
                autoSaveAndCleanup(lastStatusCache); // fallback -> enlaces
                return;
            }
            try {
                pickBtn.disabled = true;
                pickBtn.textContent = '⏳ Copiando...';
                localDirectoryHandle = await window.showDirectoryPicker();
                const label = document.getElementById('chosenFolderLabel');
                if (label) {
                    label.textContent = `Carpeta: ${localDirectoryHandle.name}`;
                    label.style.color = '#0a7523';
                }
                await autoSaveAndCleanup(lastStatusCache);
                pickBtn.textContent = '✅ Finalizado';
            } catch(e) {
                pickBtn.disabled = false;
                pickBtn.textContent = '💾 Copiar a carpeta...';
                showTemporaryMessage('❌ Cancelado');
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

    // Ya no se permite edición manual de output_dir (simplificado / oculto)

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
        btn.textContent = '⏳ Cargando archivos...';
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
                // Iniciar polling adaptativo
                startAdaptivePolling();
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
        if (!currentJobId) return;
        try {
            const response = await fetch(`${API_BASE}/cancel/${currentJobId}`, { method: 'POST' });
            if (response.ok) {
                showStatus('info', '❌ Descarga cancelada por el usuario');
                clearPolling();
                currentJobId = null;
                resetButton();
            } else {
                showStatus('error', 'No se pudo cancelar la descarga');
            }
        } catch (error) {
            showStatus('error', `Error al cancelar: ${error.message}`);
        }
    });

    // Botón global guardar todos
    const saveAllBtn = document.getElementById('saveAllBtn');
    if (saveAllBtn) {
        saveAllBtn.addEventListener('click', async () => {
            if (!lastStatusCache || !lastStatusCache.files || lastStatusCache.files.length === 0) {
                showTemporaryMessage('No hay archivos');
                return;
            }
            if (!('showDirectoryPicker' in window)) {
                showTemporaryMessage('Tu navegador no soporta carpeta (usa los botones individuales)');
                return;
            }
            try {
                saveAllBtn.disabled = true;
                const original = saveAllBtn.textContent;
                saveAllBtn.textContent = '⏳ Preparando...';
                const dirHandle = await window.showDirectoryPicker();
                const delToggle = document.getElementById('deleteAfterDownload');
                const deleteFlag = delToggle && delToggle.checked;
                const urls = lastStatusCache.download_urls || [];
                let ok=0, fail=0;
                for (let i=0;i<urls.length;i++) {
                    const url = urls[i] + (deleteFlag ? '?delete=1' : '');
                    const baseServerPath = lastStatusCache.files[i];
                    const fileName = baseServerPath.split('/').pop();
                    saveAllBtn.textContent = `⬇️ ${i+1}/${urls.length}`;
                    try {
                        const resp = await fetch(url);
                        if (!resp.ok) throw new Error(resp.status);
                        const blob = await resp.blob();
                        const fh = await dirHandle.getFileHandle(fileName, {create:true});
                        const w = await fh.createWritable();
                        await w.write(blob); await w.close();
                        ok++;
                    } catch(e) {
                        console.warn('Falló', fileName, e);
                        fail++;
                    }
                }
                saveAllBtn.textContent = `✅ ${ok} guardados${fail? ' | '+fail+' errores':''}`;
                if (deleteFlag && fail===0) {
                    // Atenuar botones individuales ya que se borraron
                    const list = document.getElementById('filesList');
                    if (list) Array.from(list.querySelectorAll('button')).forEach(b=>{ b.disabled=true; b.style.opacity='0.4'; });
                }
            } catch(err) {
                console.warn(err);
                saveAllBtn.textContent = '❌ Error';
                setTimeout(()=>{ saveAllBtn.disabled=false; saveAllBtn.textContent='💾 Guardar todos en carpeta...'; }, 2000);
                return;
            }
        });
    }
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
            }
            // Ya no mostramos el selector de carpeta: usamos enlaces directos de descarga
            const chooser = document.getElementById('folderChooserWrapper');
            if (chooser) chooser.style.display = 'none';
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
        // Añadir info de polling
        if (status.status_polls !== undefined) {
            const currentDelay = POLL_STEPS[Math.min(pollStepIndex, POLL_STEPS.length-1)]/1000;
            lines.push(`📡 Polls: <strong>${status.status_polls}</strong> (intervalo actual: ${currentDelay}s)`);
        }
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
        if (!localDirectoryHandle) {
            // Fallback: crear enlaces de descarga visibles si no hay permiso de carpeta
            console.warn('Sin handle de carpeta: modo fallback');
            const list = document.getElementById('filesList');
            if (list) {
                list.innerHTML = '';
                (status.files || []).forEach((f, i)=>{
                    const a = document.createElement('a');
                    a.href = urls[i];
                    a.textContent = f.split('/').pop();
                    a.download = f.split('/').pop();
                    a.style.display='block';
                    list.appendChild(a);
                });
            }
            return;
        }
        let saved = 0; let failed = 0;
        const havePerm = await ensureDirectoryWritePermission();
        if (!havePerm) {
            showTemporaryMessage('⚠️ Permiso escritura denegado');
            return;
        }
        for (let i=0;i<urls.length;i++) {
            const baseServerPath = (status.files && status.files[i]) || `file_${i}`;
            const baseName = baseServerPath.split('/').pop();
            try {
                const u = urls[i] + '?delete=1'; // pedir borrado tras servir
                const resp = await fetch(u);
                if (!resp.ok) throw new Error('Resp '+resp.status);
                const blob = await resp.blob();
                const fileHandle = await localDirectoryHandle.getFileHandle(baseName, {create:true});
                const writable = await fileHandle.createWritable();
                await writable.write(blob);
                await writable.close();
                saved++;
            } catch(err) {
                if (err && String(err).includes('User activation is required')) {
                    // Crear un botón manual para reintentar con interacción
                    injectManualSaveButton(status, i, baseName, urls[i]);
                }
                console.error('Fallo guardando', baseName, err);
                failed++;
            }
        }
        showTemporaryMessage(`💾 Guardados: ${saved} | Fallidos: ${failed}`);
        if (failed === 0) {
            lastStatusCache.files = []; // ya borrados en servidor
        }
    } catch(e) {
        console.warn('Auto save failed', e);
    }
}

function injectManualSaveButton(status, index, baseName, baseUrl) {
    const list = document.getElementById('filesList');
    if (!list) return;
    const wrapper = document.createElement('div');
    wrapper.style.display='flex';
    wrapper.style.alignItems='center';
    wrapper.style.gap='6px';
    const label = document.createElement('span');
    label.textContent = baseName + ' (permiso requerido)';
    label.style.fontSize='0.7rem';
    const btn = document.createElement('button');
    btn.textContent = 'Guardar ahora';
    btn.className = 'mini-btn';
    btn.style.background='#ff9800';
    btn.addEventListener('click', async ()=>{
        try {
            const granted = await ensureDirectoryWritePermission();
            if (!granted) { showTemporaryMessage('Permiso aún denegado'); return; }
            const resp = await fetch(baseUrl + '?delete=1');
            if (!resp.ok) throw new Error('Resp '+resp.status);
            const blob = await resp.blob();
            const fileHandle = await localDirectoryHandle.getFileHandle(baseName, {create:true});
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();
            wrapper.remove();
            showTemporaryMessage('✅ Guardado manual: '+baseName);
        } catch(err) {
            showTemporaryMessage('Error manual');
            console.error(err);
        }
    });
    wrapper.appendChild(label);
    wrapper.appendChild(btn);
    list.appendChild(wrapper);
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
    const urls = (lastStatusCache && lastStatusCache.download_urls) ? lastStatusCache.download_urls : [];
    files.forEach((file, idx) => {
        const fileName = file.split('/').pop();
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.gap = '10px';
        row.style.marginBottom = '6px';

        const nameSpan = document.createElement('span');
        nameSpan.textContent = fileName;
        nameSpan.style.flex = '1 1 auto';
        nameSpan.style.fontSize = '0.8rem';
        nameSpan.style.wordBreak = 'break-all';

        const btn = document.createElement('button');
        btn.textContent = '⬇️ Descargar';
        btn.className = 'mini-btn';
        btn.style.background = '#0a5b9e';
        btn.style.color = '#fff';
        btn.disabled = !urls[idx];

        btn.addEventListener('click', async () => {
            if (!urls[idx]) return;
            const delToggle = document.getElementById('deleteAfterDownload');
            const deleteFlag = delToggle && delToggle.checked;
            const finalUrl = urls[idx] + (deleteFlag ? '?delete=1' : '');
            try {
                btn.disabled = true;
                const originalText = btn.textContent;
                btn.textContent = '⏳';
                // Usamos fetch para obtener blob y forzar diálogo de descarga manual
                const resp = await fetch(finalUrl);
                if (!resp.ok) throw new Error('HTTP '+resp.status);
                const blob = await resp.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = fileName;
                document.body.appendChild(a);
                a.click();
                setTimeout(()=>{
                    URL.revokeObjectURL(a.href);
                    a.remove();
                }, 4000);
                btn.textContent = '✅';
                btn.style.background = '#2e7d32';
                if (deleteFlag) {
                    // Si se pidió borrar, podríamos remover el row tras unos segundos
                    setTimeout(()=>{ row.style.opacity='0.4'; }, 1500);
                } else {
                    // Permitir otra descarga si no se borró
                    setTimeout(()=>{ btn.disabled=false; btn.textContent=originalText; }, 1500);
                }
            } catch(err) {
                console.warn('Error descargando', err);
                btn.textContent = '❌';
                btn.style.background = '#b00020';
                setTimeout(()=>{ btn.disabled=false; btn.textContent='Reintentar'; }, 1800);
            }
        });

        row.appendChild(nameSpan);
        row.appendChild(btn);
        list.appendChild(row);
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
    clearPolling();
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

