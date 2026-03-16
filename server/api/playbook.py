
import asyncio
import json
import threading
import uuid
from pathlib import Path

import yaml
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

router = APIRouter()
_active_playbooks = {}
PLAYBOOKS_DIR = Path("playbooks")
PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_playbook_path(filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise ValueError("Invalid playbook filename")
    path = (PLAYBOOKS_DIR / filename).resolve()
    if path.parent != PLAYBOOKS_DIR.resolve():
        raise ValueError("Invalid playbook filename")
    return path

@router.get("/")
async def list_playbooks():
    files = [p.name for p in PLAYBOOKS_DIR.iterdir() if p.is_file() and p.suffix in {".yaml", ".yml"}]
    playbooks = []
    for f in files:
        try:
            with (PLAYBOOKS_DIR / f).open("r", encoding="utf-8") as stream:
                content = yaml.safe_load(stream)
                playbooks.append({"filename": f, "name": content.get("name", f), "description": content.get("description", "")})
        except:
            playbooks.append({"filename": f, "name": f, "error": "Invalid YAML"})
    return playbooks

@router.post("/run")
async def run_playbook(body: dict, background_tasks: BackgroundTasks):
    filename = body.get("filename")
    ips = body.get("ips", [])
    username = body.get("username", "")
    password = body.get("password", "")
    
    task_id = str(uuid.uuid4())
    q = asyncio.Queue()
    _active_playbooks[task_id] = q
    
    background_tasks.add_task(_execute_playbook, task_id, filename, ips, username, password)
    return {"task_id": task_id}

async def _execute_playbook(task_id, filename, ips, username, password):
    queue = _active_playbooks[task_id]
    
    try:
        playbook_path = _resolve_playbook_path(filename)
        with playbook_path.open("r", encoding="utf-8") as stream:
            pb = yaml.safe_load(stream)
        
        await queue.put({"type": "log", "text": f"🚀 Démarrage du playbook: {pb.get('name')}"})
        
        steps = pb.get("steps", [])
        for i, step in enumerate(steps):
            await queue.put({"type": "log", "text": f"--- Étape {i+1}: {step.get('name', 'Action')} ---"})
            
            if "ssh" in step:
                await _run_ssh_step(queue, ips, step["ssh"], username, password)
            elif "audit" in step:
                # Audit logic here
                pass
            
        await queue.put({"type": "log", "text": "✅ Playbook terminé avec succès."})
    except Exception as e:
        await queue.put({"type": "log", "text": f"❌ Erreur playbook: {str(e)}", "tag": "error"})
    
    await queue.put({"type": "done"})

async def _run_ssh_step(queue, ips, commands, username, password):
    if isinstance(commands, str): commands = [commands]
    
    from server.managers.ssh_manager import SSHManager
    manager = SSHManager()
    sync_q = __import__("queue").Queue()
    
    t = threading.Thread(target=manager.run_ssh_commands, args=(ips, commands, username, password, 10, sync_q), daemon=True)
    t.start()
    
    while True:
        item = sync_q.get()
        if item.get("type") == "log":
            await queue.put(item)
        if item.get("type") == "done":
            break

@router.get("/stream/{task_id}")
async def stream_playbook(task_id: str):
    async def gen():
        if task_id not in _active_playbooks:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Non trouvé'})}\n\n"
            return
        q = _active_playbooks[task_id]
        while True:
            item = await q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "done":
                _active_playbooks.pop(task_id, None)
                break
    return StreamingResponse(gen(), media_type="text/event-stream")
