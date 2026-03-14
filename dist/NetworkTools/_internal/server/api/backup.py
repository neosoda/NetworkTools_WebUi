
import asyncio
import json
import threading
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from server.db.database import get_db

router = APIRouter()
_active_backups = {}

@router.post("/start")
async def start_backup(body: dict, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    ips = body.get("ips", [])
    username = body.get("username", "")
    password = body.get("password", "")
    
    main_loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    _active_backups[task_id] = queue
    background_tasks.add_task(_run_backup, task_id, ips, username, password, main_loop)
    return {"task_id": task_id, "total": len(ips)}

@router.post("/stop/{task_id}")
async def stop_backup(task_id: str):
    manager = _active_backups.get(f"{task_id}_manager")
    if manager:
        manager.stop()
        return {"status": "stop requested"}
    return {"status": "not found"}

def _run_backup(task_id, ips, username, password, main_loop):
    sync_q = __import__("queue").Queue()
    
    from server.managers.backup_manager import BackupManager
    manager = BackupManager()
    _active_backups[f"{task_id}_manager"] = manager
    
    def worker():
        manager.run_backup(ips, username, password, sync_q)
    
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    
    queue = _active_backups[task_id]
    conn = get_db()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    while True:
        item = sync_q.get()
        asyncio.run_coroutine_threadsafe(queue.put(item), main_loop)
        
        if item.get("type") == "progress":
            # item.text format depends on BackupManager, currently "ip: status"
            text = item.get("text", "")
            if ":" in text:
                ip = text.split(":")[0].strip()
                status = text.split(":")[-1].strip()
                conn.execute("INSERT INTO backups (ip, status, timestamp) VALUES (?, ?, ?)", (ip, status, ts))
                conn.commit()
        
        if item.get("type") == "done":
            break
    
    conn.close()

@router.get("/stream/{task_id}")
async def stream_backup(task_id: str):
    async def gen():
        if task_id not in _active_backups:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Tâche non trouvée'})}\n\n"
            return
        q = _active_backups[task_id]
        while True:
            item = await q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "done":
                _active_backups.pop(task_id, None)
                break
    
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
