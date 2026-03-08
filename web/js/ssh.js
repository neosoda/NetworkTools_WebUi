// ===================== SSH MODULE =====================
let _currentSshTaskId = null;

async function loadInventoryToSSH() {
    const res = await fetch('/api/scan/last-inventory');
    const data = await res.json();
    if (data.ips?.length) {
        document.getElementById('ssh-ips').value = data.ips.join('\n');
        notify(`${data.ips.length} IPs chargées`, 'success');
    } else {
        notify('Aucun inventaire disponible', 'error');
    }
}

async function startSSH() {
    const ips = document.getElementById('ssh-ips').value.trim().split('\n').map(s => s.trim()).filter(Boolean);
    const commands = document.getElementById('ssh-commands').value.trim().split('\n').map(s => s.trim()).filter(Boolean);
    const timeout = parseInt(document.getElementById('ssh-timeout').value) || 10;
    const { username, password } = getCreds();
    
    if (!ips.length || !commands.length) return notify('IPs et commandes requises', 'error');
    if (!username || !password) return notify('Identifiants requis', 'error');
    
    document.getElementById('btn-ssh-start').disabled = true;
    document.getElementById('btn-ssh-stop').disabled = false;
    const log = document.getElementById('ssh-log');
    log.innerHTML = '';
    document.getElementById('ssh-progress-container').style.display = 'block';
    document.getElementById('ssh-progress-bar').style.width = '0%';
    
    const res = await fetch('/api/ssh/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ ips, commands, username, password, timeout })
    });
    const data = await res.json();
    _currentSshTaskId = data.task_id;
    _sshTaskId = _currentSshTaskId; // Share with panic stop
    
    let done = 0;
    const evtSource = new EventSource(`/api/ssh/stream/${_currentSshTaskId}`);
    evtSource.onmessage = (e) => {
        const item = JSON.parse(e.data);
        
        if (item.type === 'log') {
            const cls = item.tag === 'error' ? 'log-error' : item.tag === 'success' ? 'log-success' : 'log-info';
            log.innerHTML += `<div class="${cls}">[${new Date().toLocaleTimeString()}] ${escapeHtml(item.text || '')}</div>`;
            log.scrollTop = log.scrollHeight;
        }
        if (item.type === 'progress') {
            const pct = item.value !== undefined ? Math.round(item.value) : Math.min(Math.round((++done / ips.length) * 100), 100);
            document.getElementById('ssh-progress-bar').style.width = `${pct}%`;
        }
        if (item.type === 'done') {
            evtSource.close();
            document.getElementById('btn-ssh-start').disabled = false;
            document.getElementById('btn-ssh-stop').disabled = true;
            notify('Commandes SSH terminées', 'success');
            _currentSshTaskId = null;
            _sshTaskId = null;
        }
    };
}

async function stopSSH() {
    if (_currentSshTaskId) {
        await fetch(`/api/ssh/stop/${_currentSshTaskId}`, { method: 'POST' });
        notify('🛑 Arrêt SSH demandé', 'error');
        document.getElementById('btn-ssh-start').disabled = false;
        document.getElementById('btn-ssh-stop').disabled = true;
    }
}

const escapeHtml = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
