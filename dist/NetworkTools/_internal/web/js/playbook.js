// ===================== PLAYBOOK MODULE =====================
let _pbList = [];

async function loadPlaybooks() {
    const res = await fetch('/api/playbook/');
    _pbList = await res.json();
    
    const select = document.getElementById('pb-select');
    select.innerHTML = '<option value="">-- Choisir un playbook --</option>' + 
        _pbList.map(p => `<option value="${p.filename}">${p.name}</option>`).join('');
}

function loadPlaybookDetails() {
    const filename = document.getElementById('pb-select').value;
    const pb = _pbList.find(p => p.filename === filename);
    const card = document.getElementById('pb-detail-card');
    
    if (!pb) {
        card.style.display = 'none';
        return;
    }
    
    card.style.display = 'block';
    document.getElementById('pb-title').textContent = pb.name;
    document.getElementById('pb-desc').textContent = pb.description || 'Aucune description.';
}

async function runPlaybook() {
    const filename = document.getElementById('pb-select').value;
    const ipsInput = document.getElementById('pb-ips').value.trim();
    const { username, password } = getCreds();
    
    if (!filename) return notify('Veuillez choisir un playbook', 'error');
    if (!ipsInput) return notify('Veuillez saisir au moins une IP cible', 'error');
    if (!username || !password) return notify('Identifiants requis pour le playbook', 'error');
    
    const ips = ipsInput.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
    
    const log = document.getElementById('pb-log');
    log.innerHTML = '';
    
    const res = await fetch('/api/playbook/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ filename, ips, username, password })
    });
    const data = await res.json();
    
    notify('🚀 Playbook lancé...', 'info');
    
    const evtSource = new EventSource(`/api/playbook/stream/${data.task_id}`);
    evtSource.onmessage = (e) => {
        const item = JSON.parse(e.data);
        
        if (item.type === 'log') {
            const cls = item.tag === 'error' ? 'log-error' : 'log-info';
            log.innerHTML += `<div class="${cls}">${item.text}</div>`;
            log.scrollTop = log.scrollHeight;
        }
        
        if (item.type === 'done') {
            evtSource.close();
            notify('✅ Fin de l\'exécution du playbook', 'success');
        }
    };
}

// Initial load
loadPlaybooks();
