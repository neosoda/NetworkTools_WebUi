
import os
import yaml
import asyncio
import threading
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from server.db.database import get_db

router = APIRouter()
_active_playbooks = {}
PLAYBOOKS_DIR = "playbooks"

if not os.path.exists(PLAYBOOKS_DIR):
    os.makedirs(PLAYBOOKS_DIR)

@router.get("/")
async def list_playbooks():
    files = [f for f in os.listdir(PLAYBOOKS_DIR) if f.endswith(('.yaml', '.yml'))]
    playbooks = []
    for f in files:
        try:
            with open(os.path.join(PLAYBOOKS_DIR, f), 'r') as stream:
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
        with open(os.path.join(PLAYBOOKS_DIR, filename), 'r') as stream:
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
            import json
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "done":
                _active_playbooks.pop(task_id, None)
                break
    return StreamingResponse(gen(), media_type="text/event-stream")
