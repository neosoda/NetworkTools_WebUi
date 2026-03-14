// ===================== BACKUP MODULE =====================
async function loadInventoryToBackup() {
    const res = await fetch('/api/scan/last-inventory');
    const data = await res.json();
    if (data.ips?.length) {
        document.getElementById('backup-ips').value = data.ips.join('\n');
        notify(`${data.ips.length} IPs chargées depuis le dernier scan`, 'success');
    } else {
        notify('Aucun inventaire récent disponible', 'error');
    }
}

async function startBackup() {
    const ta = document.getElementById('backup-ips').value.trim();
    const ips = ta.split('\n').map(s => s.trim()).filter(Boolean);
    if (!ips.length) return notify('Veuillez saisir des adresses IP', 'error');
    
    const { username, password } = getCreds();
    if (!username || !password) return notify('Identifiants requis', 'error');
    
    const log = document.getElementById('backup-log');
    log.innerHTML = '';
    document.getElementById('backup-progress-container').style.display = 'block';
    document.getElementById('backup-progress-bar').style.width = '0%';
    
    const res = await fetch('/api/backup/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ ips, username, password })
    });
    const data = await res.json();
    _currentBackupTaskId = data.task_id;
    window._backupTaskId = data.task_id; // Share with panic stop
    
    const total = data.total || ips.length;
    let done = 0;
    
    const evtSource = new EventSource(`/api/backup/stream/${data.task_id}`);
    evtSource.onmessage = (e) => {
        const item = JSON.parse(e.data);
        
        if (item.type === 'progress') {
            done++;
            const pct = Math.round((done / total) * 100);
            document.getElementById('backup-progress-bar').style.width = `${pct}%`;
            const isErr = item.text?.includes('Erreur');
            const cls = isErr ? 'log-error' : 'log-success';
            log.innerHTML += `<div class="${cls}">[REPORT] ${item.text || ''}</div>`;
            log.scrollTop = log.scrollHeight;
        }

        if (item.type === 'log') {
            const cls = item.tag === 'error' ? 'log-error' : (item.tag === 'success' ? 'log-success' : 'log-info');
            log.innerHTML += `<div class="${cls}">${item.text}</div>`;
            log.scrollTop = log.scrollHeight;
        }
        
        if (item.type === 'done') {
            evtSource.close();
            notify(`Backup terminé : ${done}/${total} équipements traités`, 'success');
            if (item.message) log.innerHTML += `<div class="log-info" style="font-weight:bold;margin-top:10px">${item.message}</div>`;
            log.scrollTop = log.scrollHeight;
        }
        
        if (item.type === 'error') {
            log.innerHTML += `<div class="log-error">⛔ ${item.text}</div>`;
            log.scrollTop = log.scrollHeight;
        }
    };
}
