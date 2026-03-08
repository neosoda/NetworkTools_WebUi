// ===================== DIFF MODULE =====================
let _diffFiles = { 1: null, 2: null };

document.addEventListener('DOMContentLoaded', () => {
    initDropZone(1);
    initDropZone(2);
});

function initDropZone(id) {
    const zone = document.getElementById(`drop-zone-${id}`);
    const input = document.getElementById(`file-${id}`);

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFile(id, e.dataTransfer.files[0]);
    });

    input.addEventListener('change', () => {
        if (input.files.length) handleFile(id, input.files[0]);
    });
}

function handleFile(id, file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        _diffFiles[id] = {
            name: file.name,
            content: e.target.result
        };
        document.getElementById(`file-info-${id}`).textContent = `📄 ${file.name}`;
        notify(`Fichier ${id} chargé : ${file.name}`, 'info');
    };
    reader.readAsText(file);
}

function clearDiff() {
    _diffFiles = { 1: null, 2: null };
    document.getElementById('file-info-1').textContent = '';
    document.getElementById('file-info-2').textContent = '';
    document.getElementById('diff-f1').value = '';
    document.getElementById('diff-f2').value = '';
    document.getElementById('diff-result-card').style.display = 'none';
    notify('Comparateur réinitialisé', 'info');
}

async function runDiff() {
    const body = {};

    // Prioritize uploaded content
    if (_diffFiles[1]) body.text1 = _diffFiles[1].content;
    else body.file1 = document.getElementById('diff-f1').value.trim();

    if (_diffFiles[2]) body.text2 = _diffFiles[2].content;
    else body.file2 = document.getElementById('diff-f2').value.trim();

    if ((!body.text1 && !body.file1) || (!body.text2 && !body.file2)) {
        return notify('Veuillez sélectionner ou saisir deux fichiers', 'error');
    }
    
    const res = await fetch('/api/diff/compare', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    const data = await res.json();
    
    if (data.status === 'error') return notify(data.message, 'error');
    
    document.getElementById('diff-added').textContent = data.added || 0;
    document.getElementById('diff-removed').textContent = data.removed || 0;
    document.getElementById('diff-result-card').style.display = 'block';
    
    const out = document.getElementById('diff-output');
    out.innerHTML = (data.diff_lines || []).map(line => {
        if (line.startsWith('+') && !line.startsWith('+++')) return `<div class="diff-add">${escapeHtml(line)}</div>`;
        if (line.startsWith('-') && !line.startsWith('---')) return `<div class="diff-remove">${escapeHtml(line)}</div>`;
        if (line.startsWith('@')) return `<div class="diff-header">${escapeHtml(line)}</div>`;
        return `<div>${escapeHtml(line)}</div>`;
    }).join('');
    
    notify(`Comparaison terminée : +${data.added} / -${data.removed}`, data.removed > 0 ? 'error' : 'success');
}

function openDiffReport() {
    window.open('diff_report.html', '_blank');
}
