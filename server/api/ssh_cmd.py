
import asyncio
import json
import threading
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

router = APIRouter()
_active_ssh = {}

@router.post("/start")
async def start_ssh(body: dict, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    ips = body.get("ips", [])
    commands = body.get("commands", [])
    username = body.get("username", "")
    password = body.get("password", "")
    timeout = int(body.get("timeout", 10))
    
    main_loop = asyncio.get_running_loop()
    q = asyncio.Queue()
    _active_ssh[task_id] = q
    background_tasks.add_task(_run_ssh, task_id, ips, commands, username, password, timeout, main_loop)
    return {"task_id": task_id}

def _run_ssh(task_id, ips, commands, username, password, timeout, main_loop):
    sync_q = __import__("queue").Queue()
    
    from server.managers.ssh_manager import SSHManager
    manager = SSHManager()
    
    # Store for panic stop
    _active_ssh[f"{task_id}_manager"] = manager
    
    def worker():
        manager.run_ssh_commands(ips, commands, username, password, timeout, sync_q)
    
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    
    q = _active_ssh[task_id]
    while True:
        item = sync_q.get()
        asyncio.run_coroutine_threadsafe(q.put(item), main_loop)
        if item.get("type") == "done":
            break

@router.post("/stop/{task_id}")
async def stop_ssh(task_id: str):
    manager = _active_ssh.get(f"{task_id}_manager")
    if manager:
        manager.stop()
        return {"status": "stop requested"}
    return {"status": "not found"}

@router.get("/stream/{task_id}")
async def stream_ssh(task_id: str):
    async def gen():
        if task_id not in _active_ssh:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Non trouvé'})}\n\n"
            return
        q = _active_ssh[task_id]
        while True:
            item = await q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "done":
                _active_ssh.pop(task_id, None)
                _active_ssh.pop(f"{task_id}_manager", None)
                break
    
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
