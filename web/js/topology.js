// ===================== TOPOLOGY MODULE =====================
let _network = null;

async function loadTopology() {
    const container = document.getElementById('topology-container');
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted)">⏳ Chargement de la topologie...</div>';
    
    try {
        const res = await fetch('/api/topology/map');
        const data = await res.json();
        
        if (!data.nodes?.length) {
            container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted)">Aucun équipement. Lancez d\'abord un scan SNMP.</div>';
            return;
        }
        
        container.innerHTML = '';
        
        const nodes = new vis.DataSet(data.nodes.map(n => ({
            id: n.id,
            label: n.label,
            title: n.title,
            color: { background: n.color, border: n.color, highlight: { background: '#fff', border: n.color } },
            font: { color: '#e2e8f0', size: 13, face: 'Inter' },
            shape: 'dot',
            size: 18,
            shadow: { enabled: true, color: n.color, size: 10 },
            _data: n
        })));
        
        const edges = new vis.DataSet(data.edges || []);
        
        const options = {
            nodes: { borderWidth: 2, shadow: true },
            edges: { color: { color: '#2a3050' }, smooth: { type: 'curvedCW' } },
            physics: {
                barnesHut: { gravitationalConstant: -5000, centralGravity: 0.3 },
                stabilization: { iterations: 150 }
            },
            interaction: { hover: true, tooltipDelay: 200 },
            background: 'transparent'
        };
        
        if (_network) _network.destroy();
        _network = new vis.Network(container, { nodes, edges }, options);
        
        _network.on('selectNode', (params) => {
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            if (node?._data) showNodeDetail(node._data);
        });
        
        notify(`Topologie chargée : ${data.nodes.length} équipements`, 'success');
        
    } catch(e) {
        container.innerHTML = `<div style="color:var(--danger);text-align:center;margin-top:200px">Erreur : ${e.message}</div>`;
    }
}

function showNodeDetail(node) {
    const card = document.getElementById('topo-detail-card');
    const content = document.getElementById('topo-detail-content');
    card.style.display = 'block';
    content.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
            <div><div style="color:var(--text-muted);font-size:11px;text-transform:uppercase">IP</div><div style="font-family:var(--font-mono);color:var(--accent)">${node.ip}</div></div>
            <div><div style="color:var(--text-muted);font-size:11px;text-transform:uppercase">Modèle</div><div>${node.model||'—'}</div></div>
            <div><div style="color:var(--text-muted);font-size:11px;text-transform:uppercase">Localisation</div><div>${node.location||'—'}</div></div>
        </div>
        <div style="margin-top:12px;display:flex;gap:8px">
            <button class="btn btn-sm btn-ghost" onclick="document.querySelector('[data-tab=ssh]').click();setTimeout(()=>{document.getElementById('ssh-ips').value='${node.ip}'},100)">⚡ SSH</button>
        </div>`;
}

async function discoveryTopology() {
    const res = await fetch('/api/scan/last-inventory');
    const data = await res.json();
    if (!data.ips?.length) return notify('Aucun inventaire pour la découverte', 'error');
    
    notify('🔍 Découverte des liens physiques en cours...', 'info');
    await fetch('/api/topology/discover', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ ips: data.ips })
    });
    
    setTimeout(loadTopology, 3000);
}
