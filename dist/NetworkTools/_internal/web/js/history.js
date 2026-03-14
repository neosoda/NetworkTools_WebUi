// ===================== HISTORY MODULE =====================
let _currentHistoryTab = 'scans';
let _historyChart = null;

async function loadHistory(section) {
    _currentHistoryTab = section;
    
    // Load compliance trend chart
    const summary = await fetch('/api/history/audits/summary').then(r => r.json());
    if (summary.length > 0) {
        renderHistoryChart(summary.reverse());
    }
    
    showHistoryTab(section, document.querySelector('.tabs-secondary .tab-btn'));
}

async function showHistoryTab(section, el) {
    // Update button states
    document.querySelectorAll('.tabs-secondary .tab-btn').forEach(b => b.classList.remove('active'));
    if (el) el.classList.add('active');
    
    const thead = document.getElementById('history-thead');
    const tbody = document.getElementById('history-tbody');
    const data = await fetch(`/api/history/${section}`).then(r => r.json());
    
    if (section === 'scans') {
        thead.innerHTML = '<tr><th>Réseau</th><th>Démarré</th><th>Terminé</th><th>Hôtes</th><th>Statut</th></tr>';
        tbody.innerHTML = data.map(r => `
            <tr onclick="loadScanDetails(${r.id})" style="cursor:pointer">
                <td><code style="color:var(--accent)">${r.network}</code></td>
                <td style="font-size:12px">${r.started_at}</td>
                <td style="font-size:12px">${r.finished_at||'—'}</td>
                <td><span class="badge">${r.host_count||0}</span></td>
                <td><span class="badge ${r.status==='done'?'badge-success':'badge-warning'}">${r.status}</span></td>
            </tr>`).join('');
    } else if (section === 'audits') {
        thead.innerHTML = '<tr><th>IP</th><th>Règle</th><th>Statut</th><th>Détail</th><th>Date</th></tr>';
        tbody.innerHTML = data.map(r => `
            <tr>
                <td><code style="color:var(--accent)">${r.ip}</code></td>
                <td style="max-width:250px;overflow:hidden;text-overflow:ellipsis">${r.rule_name||'—'}</td>
                <td><span class="badge ${r.status==='Conforme'?'badge-success':'badge-danger'}">${r.status}</span></td>
                <td style="font-size:11px;color:var(--text-muted)">${r.detail||''}</td>
                <td style="font-size:11px">${r.timestamp}</td>
            </tr>`).join('');
    } else if (section === 'backups') {
        thead.innerHTML = '<tr><th>IP</th><th>Hostname</th><th>Statut</th><th>Archive</th><th>Date</th></tr>';
        tbody.innerHTML = data.map(r => `
            <tr>
                <td><code style="color:var(--accent)">${r.ip}</code></td>
                <td>${r.hostname||'—'}</td>
                <td><span class="badge ${r.status?.includes('Erreur')?'badge-danger':'badge-success'}">${r.status||'—'}</span></td>
                <td style="font-size:11px">${r.zip_file||'—'}</td>
                <td style="font-size:11px">${r.timestamp}</td>
            </tr>`).join('');
    }
    
    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:30px">Aucune donnée disponible. Lancez des opérations pour voir l\'historique.</td></tr>';
    }
}

async function loadScanDetails(scanId) {
    const results = await fetch(`/api/history/scans/${scanId}/results`).then(r => r.json());
    const tbody = document.getElementById('history-tbody');
    const thead = document.getElementById('history-thead');
    thead.innerHTML = '<tr><th>← <a href="#" onclick="loadHistory(\'scans\');return false" style="color:var(--accent)">Retour</a></th><th>Nom</th><th>Modèle</th><th>SNMP</th><th>Localisation</th></tr>';
    tbody.innerHTML = results.map(r => `
        <tr>
            <td><code style="color:var(--accent)">${r.ip}</code></td>
            <td>${r.name||'—'}</td>
            <td>${r.model||'—'}</td>
            <td><span class="badge badge-info">${r.snmp_version||'—'}</span></td>
            <td>${r.location||'—'}</td>
        </tr>`).join('');
}

function renderHistoryChart(data) {
    const ctx = document.getElementById('chart-history-compliance').getContext('2d');
    if (_historyChart) _historyChart.destroy();
    _historyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.timestamp?.split(' ')[0]),
            datasets: [
                { label: 'Conformes', data: data.map(d => d.ok), backgroundColor: 'rgba(34,197,94,0.6)', stack: 'audit' },
                { label: 'Non conformes', data: data.map(d => d.nok), backgroundColor: 'rgba(239,68,68,0.6)', stack: 'audit' }
            ]
        },
        options: {
            responsive: true,
            scales: { x: { stacked: true, ticks: { color: '#475569' } }, y: { stacked: true, ticks: { color: '#475569' } } },
            plugins: { legend: { labels: { color: '#94a3b8' } } }
        }
    });
}
