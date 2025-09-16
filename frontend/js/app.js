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
let downloadStartTime = null;

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
            downloadStartTime = null; // Limpiar tiempo al finalizar
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
        
        // Debug: Verificar que se está tomando la URL correcta
        const urlInput = document.getElementById('url');
        
        // Verificar que tenemos una URL
        if (!data.url || data.url.trim() === '') {
            showStatus('error', 'Por favor ingresa una URL válida');
            return;
        }
        
        // Ajustes de formato/calidad: si formato es mp4 ignorar quality
        if (data.format === 'mp4') {
            delete data.quality; // backend puede usar mejor calidad por defecto para video
        }
        // Añadir flags avanzados
        const fl = document.getElementById('force_local'); // Puede no existir tras simplificación
        if (fl) data.force_local = fl.checked ? '1' : '0';
        
        // Limpiar estado anterior y ocultar archivos de descargas previas
        lastStatusCache = null;  // Limpiar caché de estado anterior
        statusCache = {};        // Limpiar caché general
        currentJobId = null;     // Resetear job ID actual
        
        // Ocultar contenedor de archivos de descargas anteriores
        const filesContainer = document.getElementById('filesContainer');
        if (filesContainer) {
            filesContainer.style.display = 'none';
        }
        
        // Mostrar estado inicial
        showStatus('loading', 'Iniciando descarga...');
        setProgress(0, {
            task: 'Enviando solicitud al servidor...',
            stats: 'Preparando descarga'
        });
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
                downloadStartTime = Date.now(); // Registrar tiempo de inicio
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
                downloadStartTime = null; // Limpiar tiempo al cancelar
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
            if (!lastStatusCache.download_urls || lastStatusCache.download_urls.length === 0) {
                // Intentar recuperación rápida antes de salir
                await attemptRegenLinks(lastStatusCache);
                if (!lastStatusCache.download_urls || lastStatusCache.download_urls.length === 0) {
                    showTemporaryMessage('Recuperando enlaces... reintenta en 1s');
                    setTimeout(()=>{ tryRefreshSaveAll(); }, 1200);
                    return;
                }
            }
            
            try {
                // Seleccionar carpeta
                saveAllBtn.disabled = true;
                saveAllBtn.textContent = '📁 Selecciona carpeta...';
                const dirHandle = await window.showDirectoryPicker();
                
                // Comenzar descarga automáticamente
                await downloadAllFiles(dirHandle, lastStatusCache, saveAllBtn);
                
            } catch(err) {
                if (err.name === 'AbortError') {
                    saveAllBtn.textContent = '❌ Cancelado';
                } else {
                    console.warn(err);
                    saveAllBtn.textContent = '❌ Error al seleccionar carpeta';
                }
                setTimeout(()=>{ 
                    saveAllBtn.disabled = false; 
                    saveAllBtn.textContent = '💾 Guardar todos en carpeta...'; 
                }, 2000);
            }
        });
    }
});

// Función para descargar todos los archivos con manejo de errores y reintentos
async function downloadAllFiles(dirHandle, statusCache, saveAllBtn) {
    const delToggle = document.getElementById('deleteAfterDownload');
    const deleteFlag = delToggle && delToggle.checked;
    const urls = statusCache.download_urls || [];
    const files = statusCache.files || [];
    
    let successful = [];
    let failed = [];
    let retryAvailable = false;
    
    // Primera pasada: intentar descargar todos los archivos
    saveAllBtn.textContent = '⏳ Iniciando descargas...';
    
    for (let i = 0; i < urls.length; i++) {
        const url = urls[i] + (deleteFlag ? '?delete=1' : '');
        const baseServerPath = files[i];
        const fileName = baseServerPath.split('/').pop();
        
        saveAllBtn.textContent = `⬇️ Descargando ${i + 1}/${urls.length}: ${fileName.substring(0, 20)}...`;
        
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            
            const blob = await resp.blob();
            const fh = await dirHandle.getFileHandle(fileName, {create: true});
            const w = await fh.createWritable();
            await w.write(blob);
            await w.close();
            
            successful.push({index: i, fileName, url});
            
        } catch(error) {
            console.warn('Error descargando', fileName, error);
            failed.push({index: i, fileName, url, error: error.message});
        }
        
        // Pequeña pausa para evitar saturar el servidor
        if (i < urls.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }
    
    // Mostrar resultado inicial
    if (failed.length === 0) {
        // Todo exitoso
        saveAllBtn.textContent = `✅ ${successful.length} archivos guardados`;
        if (deleteFlag) {
            // Atenuar botones individuales ya que se borraron del servidor
            const list = document.getElementById('filesList');
            if (list) {
                Array.from(list.querySelectorAll('button')).forEach(b => {
                    b.disabled = true;
                    b.style.opacity = '0.4';
                });
            }
        }
        
        setTimeout(() => {
            saveAllBtn.disabled = false;
            saveAllBtn.textContent = '💾 Guardar todos en carpeta...';
        }, 3000);
        
    } else {
        // Algunos fallaron - ofrecer reintento
        retryAvailable = true;
        const successText = successful.length > 0 ? `${successful.length} ok, ` : '';
        saveAllBtn.textContent = `⚠️ ${successText}${failed.length} fallaron`;
        
        // Crear botón de reintento
        createRetryInterface(dirHandle, failed, saveAllBtn, deleteFlag);
    }
}

// Crear interfaz de reintento para archivos fallidos
function createRetryInterface(dirHandle, failedFiles, saveAllBtn, deleteFlag) {
    // Crear contenedor de reintentos si no existe
    let retryContainer = document.getElementById('retryContainer');
    if (!retryContainer) {
        retryContainer = document.createElement('div');
        retryContainer.id = 'retryContainer';
        retryContainer.style.cssText = `
            margin-top: 10px;
            padding: 12px;
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 6px;
            font-size: 0.9rem;
        `;
        
        // Insertar después del contenedor de archivos
        const filesContainer = document.getElementById('filesContainer');
        filesContainer.parentNode.insertBefore(retryContainer, filesContainer.nextSibling);
    }
    
    // Limpiar contenido previo
    retryContainer.innerHTML = '';
    
    // Título
    const title = document.createElement('div');
    title.innerHTML = `<strong>⚠️ ${failedFiles.length} archivo(s) fallaron:</strong>`;
    title.style.marginBottom = '8px';
    retryContainer.appendChild(title);
    
    // Lista de archivos fallidos
    const failedList = document.createElement('div');
    failedList.style.cssText = 'margin-bottom: 10px; max-height: 120px; overflow-y: auto;';
    
    failedFiles.forEach(file => {
        const fileDiv = document.createElement('div');
        fileDiv.style.cssText = 'font-size: 0.8rem; color: #856404; margin: 2px 0;';
        fileDiv.innerHTML = `• <strong>${file.fileName}</strong> - ${file.error}`;
        failedList.appendChild(fileDiv);
    });
    
    retryContainer.appendChild(failedList);
    
    // Botones de acción
    const buttonsDiv = document.createElement('div');
    buttonsDiv.style.cssText = 'display: flex; gap: 8px; align-items: center;';
    
    // Botón de reintentar
    const retryBtn = document.createElement('button');
    retryBtn.textContent = '🔄 Reintentar fallidos';
    retryBtn.className = 'mini-btn';
    retryBtn.style.background = '#ff9f00';
    retryBtn.style.color = 'white';
    
    retryBtn.addEventListener('click', async () => {
        retryBtn.disabled = true;
        retryBtn.textContent = '⏳ Reintentando...';
        
        let retrySuccessful = [];
        let stillFailed = [];
        
        for (let i = 0; i < failedFiles.length; i++) {
            const file = failedFiles[i];
            
            try {
                const resp = await fetch(file.url);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                
                const blob = await resp.blob();
                const fh = await dirHandle.getFileHandle(file.fileName, {create: true});
                const w = await fh.createWritable();
                await w.write(blob);
                await w.close();
                
                retrySuccessful.push(file);
                
            } catch(error) {
                console.warn('Reintento falló para', file.fileName, error);
                stillFailed.push({...file, error: error.message});
            }
            
            // Pausa entre reintentos
            if (i < failedFiles.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 200));
            }
        }
        
        // Actualizar interfaz según resultado
        if (stillFailed.length === 0) {
            // Todos los reintentos exitosos
            retryContainer.innerHTML = `
                <div style="color: #155724; background: #d4edda; padding: 8px; border-radius: 4px;">
                    ✅ <strong>¡Reintentos exitosos!</strong> ${retrySuccessful.length} archivo(s) guardado(s)
                </div>
            `;
            
            saveAllBtn.textContent = '✅ Todos los archivos guardados';
            setTimeout(() => {
                retryContainer.style.display = 'none';
                saveAllBtn.disabled = false;
                saveAllBtn.textContent = '💾 Guardar todos en carpeta...';
            }, 3000);
            
        } else {
            // Algunos siguen fallando
            if (retrySuccessful.length > 0) {
                const successDiv = document.createElement('div');
                successDiv.style.cssText = 'color: #155724; background: #d4edda; padding: 6px; border-radius: 4px; margin-bottom: 8px;';
                successDiv.innerHTML = `✅ ${retrySuccessful.length} archivo(s) guardado(s) en el reintento`;
                retryContainer.insertBefore(successDiv, retryContainer.firstChild);
            }
            
            // Recrear interfaz para los que siguen fallando
            createRetryInterface(dirHandle, stillFailed, saveAllBtn, deleteFlag);
        }
    });
    
    // Botón de ignorar
    const ignoreBtn = document.createElement('button');
    ignoreBtn.textContent = '❌ Ignorar fallidos';
    ignoreBtn.className = 'mini-btn';
    ignoreBtn.style.background = '#6c757d';
    ignoreBtn.style.color = 'white';
    
    ignoreBtn.addEventListener('click', () => {
        retryContainer.style.display = 'none';
        saveAllBtn.disabled = false;
        saveAllBtn.textContent = '💾 Guardar todos en carpeta...';
    });
    
    buttonsDiv.appendChild(retryBtn);
    buttonsDiv.appendChild(ignoreBtn);
    retryContainer.appendChild(buttonsDiv);
    
    // Resetear el botón principal
    setTimeout(() => {
        saveAllBtn.disabled = false;
        saveAllBtn.textContent = '💾 Guardar todos en carpeta...';
    }, 1000);
}

// Toggle de calidad según formato
document.addEventListener('change', function(e){
    if (e.target && e.target.id === 'format') {
        const fmt = e.target.value;
        const wrapper = document.getElementById('qualityWrapper');
        if (!wrapper) return;
        const q = document.getElementById('quality');
        // Desactivar calidad tanto para mp4 como para bestaudio (no aplica transcode)
        if (fmt === 'mp4' || fmt === 'bestaudio') {
            wrapper.style.opacity = '0.35';
            wrapper.style.pointerEvents = 'none';
            if (q) q.setAttribute('disabled','disabled');
        } else {
            wrapper.style.opacity = '1';
            wrapper.style.pointerEvents = 'auto';
            if (q) q.removeAttribute('disabled');
        }
    }
});

// Actualizar visualización del estado
function updateStatusDisplay(status) {
    // DEBUG: Imprimir en consola el resolved_output_dir y archivos listados por el backend
    if (status.resolved_output_dir) {
        console.log('[DEBUG] resolved_output_dir:', status.resolved_output_dir);
    }
    if (status.final_dir_listing) {
        console.log('[DEBUG] final_dir_listing:', status.final_dir_listing);
    }
    if (status.files) {
        console.log('[DEBUG] files:', status.files);
    }
    lastStatusCache = status; // cache
    switch (status.status) {
        case 'iniciando':
            let initTask = 'Preparando descarga...';
            let initStats = 'Configurando parámetros y validando URL';
            
            // Detectar tipo de contenido por URL
            const formData = new FormData(document.getElementById('downloadForm'));
            const url = formData.get('url') || '';
            if (url) {
                if (url.includes('/playlist?') || url.includes('list=')) {
                    initTask = 'Preparando descarga de playlist...';
                    initStats = 'Analizando contenido de la playlist';
                } else if (url.includes('/shorts/')) {
                    initTask = 'Preparando descarga de YouTube Short...';
                    initStats = 'Configurando descarga de video corto';
                } else if (url.includes('music.youtube.com')) {
                    initTask = 'Preparando descarga desde YouTube Music...';
                    initStats = 'Configurando descarga de música';
                } else {
                    initTask = 'Preparando descarga de video...';
                    initStats = 'Configurando descarga de video individual';
                }
            }
            
            showStatus('loading', 'Iniciando descarga...');
            setProgress(5, {
                task: initTask,
                stats: initStats,
                addTime: false
            });
            break;
        
        case 'descargando':
            // Usar progreso real del backend si está disponible
            let progressPercent = status.progress || 30;
            let taskInfo = 'Descargando contenido...';
            let statsInfo = '';
            
            // Información específica del progreso actual
            if (status.current_file) {
                taskInfo = status.current_file;
            } else if (status.stage === 'metadata') {
                taskInfo = 'Obteniendo información del contenido...';
                progressPercent = Math.max(progressPercent, 10);
            } else if (status.stage === 'playlist') {
                taskInfo = `Procesando playlist: ${status.playlist_name || 'Lista de reproducción'}`;
                progressPercent = Math.max(progressPercent, 15);
            } else if (status.stage === 'playlist_item') {
                taskInfo = `Descargando item ${status.current_item} de ${status.total_items}`;
                progressPercent = status.progress || progressPercent;
            } else if (status.is_playlist) {
                taskInfo = 'Descargando playlist...';
                if (status.prefetch_title) {
                    taskInfo = `Playlist: ${status.prefetch_title.substring(0, 40)}...`;
                }
            } else if (status.prefetch_title) {
                taskInfo = `Descargando: ${status.prefetch_title.substring(0, 50)}...`;
            }
            
            // Estadísticas detalladas
            const attempt = status.attempt || 1;
            const maxAttempts = status.max_attempts || 2;
            
            let statsParts = [];
            
            // Información de progreso específica
            if (status.total_size) {
                statsParts.push(`📁 ${status.total_size}`);
            }
            if (status.speed) {
                statsParts.push(`🚀 ${status.speed}`);
            }
            if (status.eta) {
                statsParts.push(`⏱️ ${status.eta}`);
            }
            
            // Información técnica
            if (attempt > 1) {
                statsParts.push(`🔄 Reintento ${attempt}/${maxAttempts}`);
                if (status.error_type) {
                    statsParts.push(`(${status.error_type})`);
                }
            } else {
                statsParts.push(`Intento ${attempt}/${maxAttempts}`);
            }
            
            if (status.anti_bot_level) {
                statsParts.push(`Anti-bot: ${status.anti_bot_level}`);
            }
            
            if (status.chosen_initial_client) {
                statsParts.push(`Cliente: ${status.chosen_initial_client}`);
            }
            
            statsInfo = statsParts.join(' • ');
            
            // Mostrar mensaje de estado específico
            let statusMessage = 'Descargando archivos...';
            if (status.current_item && status.total_items) {
                statusMessage = `Descargando item ${status.current_item} de ${status.total_items}...`;
            } else if (attempt > 1) {
                statusMessage = `Reintentando descarga (${attempt}/${maxAttempts})...`;
            } else if (status.stage === 'playlist') {
                statusMessage = 'Procesando playlist...';
            }
            
            showStatus('loading', statusMessage);
            setProgress(Math.min(progressPercent, 99), {  // No llegar a 100% hasta completar
                task: taskInfo,
                stats: statsInfo
            });
            
            // Si ya hay archivos detectados (porque estaban en cache / ya descargados) mostrarlos de inmediato
            if (status.files && status.files.length > 0 && !document.getElementById('filesContainer').style.display.includes('block')) {
                showFiles(status.files);
            }
            break;
        
        case 'completado':
            showStatus('success', '✅ Descarga completada');
            let completedStats = '';
            if (status.files && status.files.length > 0) {
                completedStats = `${status.files.length} archivo(s) descargado(s)`;
            }
            if (status.reused_existing) {
                completedStats += ' (reutilizado archivo existente)';
            }
            
            setProgress(100, {
                task: 'Descarga finalizada exitosamente',
                stats: completedStats
            });
            
            // Mostrar archivos si existen; si aún no se detectaron pero hay download_urls, forzar contenedor con nombres genéricos
            if (status.files && status.files.length > 0) {
                showFiles(status.files);
            } else if (status.download_urls && status.download_urls.length > 0) {
                const synthetic = status.download_urls.map((u,i)=>`archivo_${i+1}`);
                showFiles(synthetic);
            } else {
                // Fallback: intentar regenerar lista si terminó pero no tenemos nada
                attemptRegenLinks(status);
            }
            // Ya no mostramos el selector de carpeta: usamos enlaces directos de descarga
            const chooser = document.getElementById('folderChooserWrapper');
            if (chooser) chooser.style.display = 'none';
            if (status.stdout) {
                showLog(status.stdout);
            }
            break;
            
        case 'saltado':
            // Estado cuando se evitó re-descargar porque ya existía en archive o reuse_existing
            showStatus('info', '⚠️ Ya estaba descargado (saltado)');
            let skippedStats = '';
            if (status.files && status.files.length > 0) {
                skippedStats = `${status.files.length} archivo(s) encontrado(s)`;
            }
            if (status.already_downloaded) {
                skippedStats += ' (ya en archivo de descargas)';
            }
            
            setProgress(100, {
                task: 'Contenido ya disponible - descarga omitida',
                stats: skippedStats
            });
            
            if (status.files && status.files.length > 0) {
                showFiles(status.files);
            } else if (status.download_urls && status.download_urls.length > 0) {
                const synthetic2 = status.download_urls.map((u,i)=>`archivo_${i+1}`);
                showFiles(synthetic2);
            } else {
                // Intentar fallback inmediato para forzar aparición módulo archivos
                attemptRegenLinks(status, true);
            }
            break;
        
        case 'error':
            showStatus('error', `❌ Error: ${status.error}`);
            let errorStats = '';
            if (status.attempt) {
                errorStats = `Falló en intento ${status.attempt}`;
            }
            if (status.error_type) {
                errorStats += ` • Tipo: ${status.error_type}`;
            }
            
            setProgress(0, {
                task: 'Error durante la descarga',
                stats: errorStats
            });
            
            if (status.stdout) {
                showLog(`Error:\n${status.error}\n\nOutput:\n${status.stdout}`);
            }
            break;
        
        case 'cancelado':
            showStatus('info', '❌ Descarga cancelada');
            setProgress(0, {
                task: 'Descarga cancelada por el usuario',
                stats: 'Proceso interrumpido'
            });
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

// Intentar regenerar enlaces/archivos desde backend si el frontend no recibió download_urls
async function attemptRegenLinks(status, showMsg=false){
    try {
        if (!currentJobId) return;
        if (showMsg) showTemporaryMessage('Intentando recuperar archivos...');
        // Primero usar endpoint GET (idempotente) para obtener siempre urls
        let resp = await fetch(`${API_BASE}/job-files/${currentJobId}`);
        let data = await resp.json();
        if (!(data && data.files && data.files.length)) {
            // fallback a POST legacy
            resp = await fetch(`${API_BASE}/regen-files/${currentJobId}`, {method:'POST'});
            data = await resp.json();
        }
        if (data && data.files && data.files.length){
            // Forzar un nuevo poll status para que el estado normal tenga download_urls
            setTimeout(()=>{ checkStatus(); tryRefreshSaveAll(); }, 400);
        } else {
            injectRecoverButton();
        }
    } catch(e){
        injectRecoverButton();
    }
}

function injectRecoverButton(){
    const container = document.getElementById('filesContainer');
    if (!container) return;
    container.style.display='block';
    const list = document.getElementById('filesList');
    if (!list) return;
    if (list.querySelector('.recover-btn')) return; // evitar duplicados
    const wrapper = document.createElement('div');
    wrapper.style.padding='8px';
    wrapper.style.background='#222';
    wrapper.style.borderRadius='6px';
    wrapper.style.fontSize='0.75rem';
    wrapper.textContent='No se pudieron generar los enlaces de archivos. Pulsa para reintentar.';
    const btn = document.createElement('button');
    btn.textContent='🔄 Recuperar enlaces';
    btn.className='mini-btn recover-btn';
    btn.style.background='#6a1b9a';
    btn.addEventListener('click', ()=>{
        btn.disabled=true; btn.textContent='⏳';
        attemptRegenLinks(lastStatusCache);
        setTimeout(()=>{ btn.disabled=false; btn.textContent='🔄 Recuperar enlaces'; }, 3000);
    });
    wrapper.appendChild(document.createElement('br'));
    wrapper.appendChild(btn);
    list.appendChild(wrapper);
}

function tryRefreshSaveAll(){
    const saveAllBtn = document.getElementById('saveAllBtn');
    if (!saveAllBtn) return;
    if (lastStatusCache && lastStatusCache.download_urls && lastStatusCache.download_urls.length){
        saveAllBtn.disabled = false;
        if (!saveAllBtn.textContent.includes('Guardar')) {
            saveAllBtn.textContent='💾 Guardar todos en carpeta...';
        }
    }
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
function setProgress(percent, details = null) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const downloadDetails = document.getElementById('downloadDetails');
    const currentTask = document.getElementById('currentTask');
    const downloadStats = document.getElementById('downloadStats');
    
    progressFill.style.width = `${percent}%`;
    progressText.textContent = `${Math.round(percent)}%`;
    
    if (details) {
        downloadDetails.style.display = 'block';
        if (details.task) {
            currentTask.textContent = details.task;
        }
        if (details.stats) {
            let statsText = details.stats;
            
            // Agregar tiempo transcurrido si la descarga ha iniciado
            if (downloadStartTime && (percent > 0 || details.addTime !== false)) {
                const elapsed = Math.floor((Date.now() - downloadStartTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
                statsText += ` • Tiempo: ${timeStr}`;
            }
            
            downloadStats.textContent = statsText;
        }
    } else {
        downloadDetails.style.display = 'none';
    }
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
    const filesContainer = document.getElementById('filesContainer');
    const filesList = document.getElementById('filesList');
    
    // Ocultar contenedor
    filesContainer.style.display = 'none';
    
    // Limpiar contenido de la lista
    if (filesList) {
        filesList.innerHTML = '';
    }
    
    // Limpiar también cualquier interfaz de reintento que pueda existir
    const retryContainer = document.getElementById('retryContainer');
    if (retryContainer) {
        retryContainer.style.display = 'none';
        retryContainer.innerHTML = '';
    }
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

// Inicialización del botón de descarga principal
document.addEventListener('DOMContentLoaded', function() {
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadForm = document.getElementById('downloadForm');
    
    // Asegurar que el botón funcione tanto por submit del form como por click directo
    if (downloadBtn && downloadForm) {
        downloadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            downloadForm.dispatchEvent(new Event('submit'));
        });
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

