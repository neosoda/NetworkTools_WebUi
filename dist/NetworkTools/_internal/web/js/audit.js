// ===================== AUDIT MODULE =====================
let _auditOk = 0, _auditNok = 0;

async function startAudit() {
    const ips = document.getElementById('audit-ips').value.trim().split('\n').map(s=>s.trim()).filter(Boolean);
    const config_content = document.getElementById('audit-config').value.trim();
    const mode = document.getElementById('audit-mode').value;
    const should_exist = document.getElementById('audit-logic').value === 'true';
    const { username, password } = getCreds();
    
    if (!ips.length || !config_content) return notify('IPs et règles requises', 'error');
    if (!username || !password) return notify('Identifiants requis', 'error');
    
    const tbody = document.getElementById('audit-tbody');
    tbody.innerHTML = '';
    _auditOk = 0; _auditNok = 0;
    updateAuditCounters();
    
    const res = await fetch('/api/audit/start', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ ips, config_content, mode, should_exist, username, password })
    });
    const data = await res.json();
    window._auditTaskId = data.task_id;
    
    const evtSource = new EventSource(`/api/audit/stream/${data.task_id}`);
    evtSource.onmessage = (e) => {
        const item = JSON.parse(e.data);
        
        if (item.type === 'result') {
            const isOk = item.status === 'Conforme';
            if (isOk) _auditOk++; else _auditNok++;
            updateAuditCounters();
            
            const badgeCls = isOk ? 'badge-success' : 'badge-danger';
            const rowData = { ip: item.ip, rule: item.rule };
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><code style="color:var(--accent)">${item.ip}</code></td>
                <td style="max-width:300px">${item.rule||''}</td>
                <td><span class="badge ${badgeCls}">${item.status}</span></td>
                <td style="font-size:11px;color:var(--text-muted)">${item.detail||''}</td>
                <td>
                    <button class="btn btn-sm btn-ghost" onclick='showContextMenu(event, ${JSON.stringify(rowData)})'>⋮</button>
                </td>`;
            tbody.appendChild(tr);
        }
        
        if (item.type === 'done') {
            evtSource.close();
            notify(`Audit terminé : ${_auditOk} conformes, ${_auditNok} non conformes`, _auditNok > 0 ? 'error' : 'success');
        }
    };
}

function updateAuditCounters() {
    document.getElementById('audit-ok-count').textContent = `✅ ${_auditOk}`;
    document.getElementById('audit-nok-count').textContent = `❌ ${_auditNok}`;
}
