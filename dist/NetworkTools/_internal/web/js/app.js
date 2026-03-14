// ===================== CORE APP =====================
// Navigation + Context Menu + Notifications + Panic Stop

// Tab navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.dataset.tab;
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        item.classList.add('active');
        document.getElementById(`tab-${tab}`).classList.add('active');
        if (tab === 'dashboard') loadDashboard();
        if (tab === 'topology') loadTopology();
        if (tab === 'history') loadHistory('scans');
        if (tab === 'scheduler') loadScheduler();
    });
});

// Global credentials
const getCreds = () => ({
    username: document.getElementById('g-username').value,
    password: document.getElementById('g-password').value,
    community: document.getElementById('g-community').value,
});

// ─── UTILS ───
const notify = (msg, type='info') => {
    const n = document.getElementById('notification-bar');
    n.textContent = msg;
    n.className = `notification ${type}`;
    n.classList.remove('hidden');
    setTimeout(() => n.classList.add('hidden'), 3500);
};

window.copyToClipboard = function(text) {
    if (!navigator.clipboard) {
        // Fallback pour les contextes non sécurisés si nécessaire
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            notify('Copié (fallback) !', 'success');
        } catch (err) {
            notify('Erreur de copie', 'error');
        }
        document.body.removeChild(textArea);
        return;
    }
    navigator.clipboard.writeText(text).then(() => {
        notify('Copié dans le presse-papier !', 'success');
    }).catch(err => {
        notify('Erreur de copie', 'error');
    });
}

// ─── PANIC STOP ───
let _sshTaskId = null;
window._backupTaskId = null;

const panicStop = async () => {
    if (_sshTaskId) {
        await fetch(`/api/ssh/stop/${_sshTaskId}`, { method: 'POST' });
        _sshTaskId = null;
    }
    if (window._backupTaskId) {
        await fetch(`/api/backup/stop/${window._backupTaskId}`, { method: 'POST' });
        window._backupTaskId = null;
    }
    if (window._auditTaskId) {
        await fetch(`/api/audit/stop/${window._auditTaskId}`, { method: 'POST' });
        window._auditTaskId = null;
    }
    notify('🛑 Arrêt total demandé', 'error');
    document.querySelectorAll('.progress-bar-fill').forEach(b => b.style.width = '0%');
};

// Theme Management
function toggleTheme() {
    const isLight = document.body.classList.toggle('light-mode');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    document.getElementById('theme-btn').textContent = isLight ? '☀️' : '🌙';
}

function initTheme() {
    if (localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light-mode');
        document.getElementById('theme-btn').textContent = '☀️';
    }
}

// ─── CONTEXT MENU ───
let _ctxRow = null;
document.addEventListener('click', () => {
    document.getElementById('context-menu').style.display = 'none';
});

const showContextMenu = (event, rowData) => {
    event.preventDefault();
    _ctxRow = rowData;
    const menu = document.getElementById('context-menu');
    menu.style.display = 'block';
    menu.style.left = `${event.clientX}px`;
    menu.style.top = `${event.clientY}px`;
};

document.getElementById('ctx-copy-ip').onclick = () => {
    if (_ctxRow?.ip) {
        navigator.clipboard.writeText(_ctxRow.ip).then(() => notify(`IP ${_ctxRow.ip} copiée ! `, 'success'));
    }
};

document.getElementById('ctx-remediate').onclick = async () => {
    if (!_ctxRow) return;
    const res = await fetch('/api/audit/remediate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ ip: _ctxRow.ip, rule: _ctxRow.rule })
    });
    const data = await res.json();
    document.getElementById('modal-code-content').textContent = data.remediation_script;
    document.getElementById('modal-remediation').classList.add('show');
};

document.getElementById('ctx-ssh').onclick = () => {
    if (_ctxRow?.ip) {
        document.querySelector('[data-tab="ssh"]').click();
        setTimeout(() => {
            const ta = document.getElementById('ssh-ips');
            ta.value = _ctxRow.ip;
        }, 100);
    }
};

// ─── MODAL ───
const closeModal = () => document.getElementById('modal-remediation').classList.remove('show');
const copyRemediationScript = () => {
    const code = document.getElementById('modal-code-content').textContent;
    navigator.clipboard.writeText(code).then(() => notify('Script copié !', 'success'));
};

// ─── DASHBOARD LOAD ───
async function loadDashboard() {
    try {
        const [audits, scans, backups] = await Promise.all([
            fetch('/api/history/audits/summary').then(r => r.json()),
            fetch('/api/history/scans').then(r => r.json()),
            fetch('/api/history/backups').then(r => r.json()),
        ]);

        // Stats
        const lastScan = scans[0];
        document.getElementById('stat-hosts').textContent = lastScan?.host_count ?? '—';
        
        const ok = audits.reduce((a,b) => a + (b.ok || 0), 0);
        const nok = audits.reduce((a,b) => a + (b.nok || 0), 0);
        document.getElementById('stat-compliant').textContent = ok || '—';
        document.getElementById('stat-noncompliant').textContent = nok || '—';
        document.getElementById('stat-backups').textContent = backups.length || '—';

        // Compliance trend chart
        if (audits.length > 0) {
            renderComplianceChart(audits.reverse());
        }

        // Activity chart
        if (scans.length > 0) {
            renderActivityChart(scans.slice(0, 10).reverse());
        }

        // Recent hosts
        if (lastScan?.id) {
            const results = await fetch(`/api/history/scans/${lastScan.id}/results`).then(r => r.json());
            const tbody = document.querySelector('#tbl-recent-hosts tbody');
            tbody.innerHTML = results.slice(0, 10).map(r =>
                `<tr><td><code>${r.ip}</code></td><td>${r.name||'—'}</td><td>${r.model||'—'}</td>
                 <td><span class="badge badge-info">${r.snmp_version||'—'}</span></td><td>${r.location||'—'}</td></tr>`
            ).join('');
        }
    } catch(e) { console.warn('Dashboard load error:', e); }
}

function renderComplianceChart(data) {
    const ctx = document.getElementById('chart-compliance').getContext('2d');
    if (window._chartCompliance) window._chartCompliance.destroy();
    window._chartCompliance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.timestamp?.split(' ')[0]),
            datasets: [
                { label: 'Conformes', data: data.map(d => d.ok), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', tension: 0.4, fill: true },
                { label: 'Non conformes', data: data.map(d => d.nok), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', tension: 0.4, fill: true }
            ]
        },
        options: { responsive: true, plugins: { legend: { labels: { color: '#94a3b8' } } }, scales: { x: { ticks: { color: '#475569' } }, y: { ticks: { color: '#475569' } } } }
    });
}

function renderActivityChart(scans) {
    const ctx = document.getElementById('chart-activity').getContext('2d');
    if (window._chartActivity) window._chartActivity.destroy();
    window._chartActivity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: scans.map(s => s.started_at?.split(' ')[0]),
            datasets: [{ label: 'Équipements', data: scans.map(s => s.host_count), backgroundColor: 'rgba(79,140,255,0.4)', borderColor: '#4f8cff', borderWidth: 1 }]
        },
        options: { responsive: true, scales: { x: { ticks: { color: '#475569' } }, y: { ticks: { color: '#475569' } } }, plugins: { legend: { labels: { color: '#94a3b8' } } } }
    });
}

// Load dashboard on start
loadDashboard();
