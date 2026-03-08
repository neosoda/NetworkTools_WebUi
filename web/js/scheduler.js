// ===================== SCHEDULER MODULE =====================
async function loadScheduler() {
    const res = await fetch('/api/scheduler/tasks');
    const tasks = await res.json();
    
    const tbody = document.getElementById('scheduler-tbody');
    if (!tasks.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:30px">Aucune tâche planifiée. Créez votre première automatisation ci-dessus.</td></tr>';
        return;
    }
    
    tbody.innerHTML = tasks.map(t => `
        <tr>
            <td><strong>${t.name}</strong></td>
            <td><span class="badge">${t.task_type}</span></td>
            <td><code style="font-size:11px;color:var(--accent)">${t.cron_expr}</code></td>
            <td><span class="badge ${t.enabled ? 'badge-success' : ''}">${t.enabled ? '✅ Actif' : '⏸️ Pausé'}</span></td>
            <td>
                <button class="btn btn-sm btn-ghost" onclick="toggleTask(${t.id})">${t.enabled ? 'Pause' : 'Activer'}</button>
                <button class="btn btn-sm btn-danger" onclick="deleteTask(${t.id})">Supprimer</button>
            </td>
        </tr>`).join('');
}

async function createScheduledTask() {
    const name = document.getElementById('sched-name').value.trim();
    const task_type = document.getElementById('sched-type').value;
    const dateVal = document.getElementById('sched-date').value;
    
    if (!name || !dateVal) return notify('Nom et date requis', 'error');
    
    // Convert date to a cron string for the backend (which expects cron_expr)
    // format: YYYY-MM-DDTHH:mm -> we extract min, hour, day, month
    const d = new Date(dateVal);
    const cron_expr = `${d.getMinutes()} ${d.getHours()} ${d.getDate()} ${d.getMonth() + 1} *`;
    
    await fetch('/api/scheduler/tasks', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name, task_type, cron_expr })
    });
    
    document.getElementById('sched-name').value = '';
    document.getElementById('sched-date').value = '';
    notify(`Tâche "${name}" programmée`, 'success');
    loadScheduler();
}

async function toggleTask(id) {
    await fetch(`/api/scheduler/tasks/${id}/toggle`, { method: 'PUT' });
    loadScheduler();
}

async function deleteTask(id) {
    if (!confirm('Supprimer cette tâche planifiée ?')) return;
    await fetch(`/api/scheduler/tasks/${id}`, { method: 'DELETE' });
    notify('Tâche supprimée', 'info');
    loadScheduler();
}
