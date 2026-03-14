// ===================== SCAN MODULE =====================
let _scanId = null;

async function startScan() {
    const network = document.getElementById('scan-network').value.trim();
    if (!network) return notify('Veuillez saisir un réseau (CIDR)', 'error');
    
    const btn = document.getElementById('btn-scan');
    btn.disabled = true;
    btn.textContent = '⏳ Scan en cours...';
    
    const tbody = document.querySelector('#tbl-scan-results tbody');
    tbody.innerHTML = '';
    document.getElementById('scan-result-count').textContent = '0 hôtes';
    
    const container = document.getElementById('scan-progress-container');
    container.style.display = 'block';
    document.getElementById('scan-progress-bar').style.width = '0%';
    document.getElementById('scan-progress-label').textContent = 'Initialisation du scan...';
    
    try {
        const res = await fetch('/api/scan/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ network })
        });
        const data = await res.json();
        _scanId = data.scan_id;
        
        // Open SSE stream
        const evtSource = new EventSource(`/api/scan/stream/${_scanId}`);
        let count = 0;
        
        evtSource.onmessage = (e) => {
            const item = JSON.parse(e.data);
            
            if (item.type === 'progress') {
                const pct = Math.round(item.value || 0);
                document.getElementById('scan-progress-bar').style.width = `${pct}%`;
                document.getElementById('scan-progress-label').textContent = `Progression: ${pct}%`;
            }
            
            if (item.type === 'result' || item.type === 'log') {
                // Add row if result has IP info
                if (item.ip) {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td onclick="copyToClipboard('${item.ip}')" style="cursor:pointer" title="Cliquez pour copier">
                            <code style="color:var(--accent)">${item.ip}</code>
                        </td>
                        <td>${item.name||'—'}</td>
                        <td>${item.model||'—'}</td>
                        <td><span class="badge badge-info">${item.snmp||'—'}</span></td>
                        <td style="font-family:var(--font-mono);font-size:11px">${item.mac||'—'}</td>
                        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${item.desc||''}">${(item.desc||'—').substring(0,60)}</td>
                        <td>${item.location||'—'}</td>`;
                    tbody.prepend(tr);
                    count++;
                    document.getElementById('scan-result-count').textContent = `${count} hôtes`;
                }
            }

window.copyAllScanIPs = function() {
    const ips = Array.from(document.querySelectorAll('#tbl-scan-results tbody td:first-child code'))
                     .map(code => code.textContent);
    if (ips.length === 0) return notify('Aucune IP à copier', 'warning');
    copyToClipboard(ips.join(', '));
}
            
            if (item.type === 'error') {
                notify(`Erreur scan: ${item.text}`, 'error');
            }
            
            if (item.type === 'done') {
                evtSource.close();
                btn.disabled = false;
                btn.textContent = '🔍 Lancer le scan';
                document.getElementById('scan-progress-label').textContent = `Scan terminé — ${count} équipements trouvés`;
                document.getElementById('scan-progress-bar').style.width = '100%';
                notify(`Scan terminé : ${count} équipements découverts`, 'success');
                
                if (item.file) {
                    notify('📊 Ouverture du rapport Excel...', 'info');
                    window.open(`/api/download/${item.file}`, '_blank');
                }
                
                loadDashboard();
            }
        };
        
        evtSource.onerror = () => {
            evtSource.close();
            btn.disabled = false;
            btn.textContent = '🔍 Lancer le scan';
        };
        
    } catch(e) {
        notify(`Erreur: ${e}`, 'error');
        btn.disabled = false;
        btn.textContent = '🔍 Lancer le scan';
    }
}
