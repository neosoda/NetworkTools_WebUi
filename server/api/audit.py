
import asyncio
import json
import threading
import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
import re
from server.db.database import get_db

router = APIRouter()
_active_audits = {}

def load_config():
    from server.utils.paths import get_file_path
    import os
    try:
        config_path = get_file_path("config.json")
        if not os.path.exists(config_path):
             return {"settings": {}, "audit_rules": []}
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"settings": {}, "audit_rules": []}

@router.post("/start")
async def start_audit(body: dict, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    ips = body.get("ips", [])
    username = body.get("username", "")
    password = body.get("password", "")
    config_content = body.get("config_content", "")
    mode = body.get("mode", "line")
    should_exist = body.get("should_exist", True)
    
    # Generate rules from content
    rules = _build_rules(config_content, mode, should_exist)
    
    main_loop = asyncio.get_running_loop()
    q = asyncio.Queue()
    _active_audits[task_id] = q
    background_tasks.add_task(_run_audit, task_id, ips, username, password, rules, main_loop)
    return {"task_id": task_id, "rules_count": len(rules)}

def _build_rules(config_content, mode, should_exist):
    verb = "Check" if should_exist else "Forbid"
    rules = []
    
    if not config_content.strip():
        return rules
    
    if mode == "block":
        words = config_content.split()
        if words:
            safe_pattern = r"\s+".join([re.escape(p) for p in words])
            rules.append({
                "name": f"{verb} Bloc: {' '.join(words[:4])}...", 
                "pattern": safe_pattern, 
                "should_exist": should_exist,
                "type": "block",
                "original_words": words
            })
    else:
        for line in config_content.split("\n"):
            line = line.strip()
            if line:
                words = line.split()
                pattern = r"\s+".join([re.escape(p) for p in words])
                rules.append({
                    "name": f"{verb} {line}"[:60], 
                    "pattern": pattern, 
                    "should_exist": should_exist,
                    "type": "line",
                    "original_words": words
                })
    return rules

@router.post("/stop/{task_id}")
async def stop_audit(task_id: str):
    manager = _active_audits.get(f"{task_id}_manager")
    if manager:
        manager.stop()
        return {"status": "stop requested"}
    return {"status": "not found"}

def _run_audit(task_id, ips, username, password, rules, main_loop):
    sync_q = __import__("queue").Queue()
    
    from server.managers.audit_manager import AuditManager
    manager = AuditManager()
    _active_audits[f"{task_id}_manager"] = manager
    
    def worker():
        manager.run_audit(ips, username, password, rules, sync_q)
    
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    
    conn = get_db()
    q = _active_audits[task_id]
    session_id = task_id
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    while True:
        item = sync_q.get()
        asyncio.run_coroutine_threadsafe(q.put(item), main_loop)
        
        if item.get("type") == "result":
            conn.execute(
                "INSERT INTO audit_results (session_id, ip, rule_name, status, detail, timestamp) VALUES (?,?,?,?,?,?)",
                (session_id, item.get("ip"), item.get("rule"), item.get("status"), item.get("detail", ""), ts)
            )
            conn.commit()
        
        if item.get("type") == "done":
            break
    conn.close()

@router.get("/stream/{task_id}")
async def stream_audit(task_id: str):
    async def gen():
        if task_id not in _active_audits:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Non trouvé'})}\n\n"
            return
        q = _active_audits[task_id]
        while True:
            item = await q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "done":
                _active_audits.pop(task_id, None)
                break
    
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.post("/remediate")
async def remediate(body: dict):
    """Generate CLI remediation script for a failed rule."""
    rule_name = body.get("rule", "")
    ip = body.get("ip", "")
    
    cmd = "configure terminal\n"
    r = rule_name.lower()
    if "password-encryption" in r: cmd += "service password-encryption\n"
    elif "banner" in r: cmd += "no banner motd\nno banner exec\nno banner login\n"
    elif "ssh" in r: cmd += "ip domain-name local.lab\ncrypto key generate rsa modulus 2048\nip ssh version 2\nip ssh time-out 60\nip ssh authentication-retries 3\n"
    elif "http" in r or "web" in r: cmd += "no ip http server\nno ip http secure-server\n"
    elif "telnet" in r: cmd += "line vty 0 15\ntransport input ssh\n"
    elif "snmp" in r: cmd += "no snmp-server community public\nno snmp-server community private\n"
    elif "ntp" in r: cmd += "ntp server 8.8.8.8\n"
    elif "logging" in r: cmd += "logging buffered 16384\nlogging trap notifications\n"
    else: cmd += f"! TODO : Corriger manuellement la règle '{rule_name}'\n"
    cmd += "end\nwrite memory"
    
    return {"ip": ip, "rule": rule_name, "remediation_script": cmd}
