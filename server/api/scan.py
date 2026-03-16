
import asyncio
import json
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from server.db.database import get_db
from server.utils.paths import get_file_path

router = APIRouter()

# Global task registry
_active_scans = {}

def load_config():
    try:
        config_path = get_file_path("config.json")
        if not os.path.exists(config_path):
             return {"settings": {"snmp_communities": ["public"], "ip_scan_limit_last_octet": 254}, "oids": {}}
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"settings": {"snmp_communities": ["public"], "ip_scan_limit_last_octet": 254}, "oids": {}}

@router.post("/start")
async def start_scan(body: dict, background_tasks: BackgroundTasks):
    scan_id = str(uuid.uuid4())
    network = body.get("network", "192.168.1.0/24")
    
    # Register scan in DB
    conn = get_db()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO scans (network, started_at, status) VALUES (?, ?, 'running')", (network, ts))
    conn.commit()
    db_scan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    main_loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    _active_scans[scan_id] = {"queue": queue, "db_id": db_scan_id}
    
    background_tasks.add_task(_run_scan, scan_id, db_scan_id, network, main_loop)
    return {"scan_id": scan_id, "db_id": db_scan_id}

def _run_scan(scan_id: str, db_id: int, network: str, main_loop):
    """Run scan in thread, push results to queue."""
    import threading, asyncio
    
    from server.managers.snmp_manager import SNMPManager
    config = load_config()
    queue = _active_scans[scan_id]["queue"]
    
    sync_queue = __import__("queue").Queue()
    manager = SNMPManager()
    
    def worker():
        manager.run_snmp_scan(network, config, sync_queue)
    
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    
    results = []
    results_count = 0
    while True:
        item = sync_queue.get()
        # Forward to async queue using the MAIN loop
        asyncio.run_coroutine_threadsafe(queue.put(item), main_loop)
        
        if item.get("type") == "result":
            # Save individual host to DB
            try:
                conn = get_db()
                conn.execute(
                    """INSERT INTO scan_results 
                       (scan_id, ip, snmp_version, mac, name, model, description, location, timestamp) 
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (db_id, item.get("ip"), item.get("snmp"), item.get("mac"), 
                     item.get("name"), item.get("model"), item.get("desc"), 
                     item.get("location"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                conn.close()
                results_count += 1
            except Exception as e:
                print(f"Error saving host to DB: {e}")
        
        if item.get("type") == "done":
            break
        if item.get("type") == "progress":
            pass  # Just forward
    
    # Update scan status
    conn = get_db()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE scans SET finished_at=?, status='done', host_count=? WHERE id=?",
                 (ts, results_count, db_id))
    conn.commit()
    conn.close()

@router.get("/stream/{scan_id}")
async def stream_scan(scan_id: str):
    """Server-Sent Events stream for real-time progress."""
    async def event_generator():
        if scan_id not in _active_scans:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Scan non trouvé'})}\n\n"
            return
        
        queue = _active_scans[scan_id]["queue"]
        while True:
            item = await queue.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "done":
                _active_scans.pop(scan_id, None)
                break
    
    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.get("/last-inventory")
async def get_last_inventory():
    """Return IP list from last scan cache."""
    import os
    cache_file = get_file_path("last_inventory.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return {"ips": json.load(f)}
    return {"ips": []}
