import asyncio
import json
import threading
import uuid
import queue
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from server.managers.ssh_manager import SSHManager

router = APIRouter()
_active_ssh: Dict[str, Any] = {}

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

def _run_ssh(task_id: str, ips: List[str], commands: List[str], username: str, password: str, timeout: int, main_loop: asyncio.AbstractEventLoop):
    sync_q = queue.Queue()
    manager = SSHManager()
    
    # Store for panic stop
    _active_ssh[f"{task_id}_manager"] = manager
    
    def worker():
        manager.run_ssh_commands(ips, commands, username, password, timeout, sync_q)
    
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    
    q = _active_ssh[task_id]
    log_buffer = []
    
    while True:
        item = sync_q.get()
        
        if item.get("type") == "log":
            text = item.get("text", "")
            log_buffer.append(text)
            asyncio.run_coroutine_threadsafe(q.put(item), main_loop)
            
        elif item.get("type") == "done":
            # Save consolidated log to file BEFORE sending the DONE signal
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"ssh_mass_report_{timestamp}.txt"
            try:
                with open(report_filename, "w", encoding="utf-8") as f:
                    f.write(f"=== RAPPORT SSH MASS ({timestamp}) ===\n")
                    f.write(f"Cibles: {len(ips)} équipement(s)\n")
                    f.write("=" * 50 + "\n\n")
                    f.write("\n".join(log_buffer))
                    f.write("\n\n" + "=" * 50 + "\n=== FIN DU RAPPORT ===")
                
                report_item = {"type": "report_ready", "file": report_filename}
                asyncio.run_coroutine_threadsafe(q.put(report_item), main_loop)
            except Exception as e:
                print(f"Failed to write ssh report: {e}")
            
            asyncio.run_coroutine_threadsafe(q.put(item), main_loop)
            break
            
        else:
            asyncio.run_coroutine_threadsafe(q.put(item), main_loop)

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
