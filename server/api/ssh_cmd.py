import asyncio
import ipaddress
import json
import queue
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from server.managers.ssh_manager import SSHManager
from server.utils.paths import get_app_data_dir

router = APIRouter()
_active_ssh: dict[str, Any] = {}


class StartSSHRequest(BaseModel):
    ips: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    username: str = Field(default="", max_length=128)
    password: str = Field(default="", max_length=256)
    timeout: int = Field(default=10, ge=1, le=120)

    @field_validator("ips")
    @classmethod
    def validate_ips(cls, value: list[str]) -> list[str]:
        sanitized: list[str] = []
        for ip in value:
            candidate = ip.strip()
            try:
                ipaddress.ip_address(candidate)
            except ValueError as exc:
                raise ValueError(f"Invalid IP address: {candidate}") from exc
            sanitized.append(candidate)
        return sanitized

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, value: list[str]) -> list[str]:
        sanitized = [cmd.strip() for cmd in value if cmd and cmd.strip()]
        if not sanitized:
            raise ValueError("At least one command is required")
        return sanitized

@router.post("/start")
async def start_ssh(body: StartSSHRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    task_id = str(uuid.uuid4())

    main_loop = asyncio.get_running_loop()
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _active_ssh[task_id] = q
    background_tasks.add_task(
        _run_ssh,
        task_id,
        body.ips,
        body.commands,
        body.username,
        body.password,
        body.timeout,
        main_loop,
    )
    return {"task_id": task_id}


def _report_path(timestamp: str) -> Path:
    report_name = f"ssh_mass_report_{timestamp}.txt"
    return Path(get_app_data_dir()).resolve() / report_name


def _run_ssh(
    task_id: str,
    ips: list[str],
    commands: list[str],
    username: str,
    password: str,
    timeout: int,
    main_loop: asyncio.AbstractEventLoop,
) -> None:
    sync_q: queue.Queue[dict[str, Any]] = queue.Queue()
    manager = SSHManager()

    # Store for panic stop
    _active_ssh[f"{task_id}_manager"] = manager

    def worker():
        manager.run_ssh_commands(ips, commands, username, password, timeout, sync_q)

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    q = _active_ssh[task_id]
    log_buffer: list[str] = []

    while True:
        item = sync_q.get()

        if item.get("type") == "log":
            text = item.get("text", "")
            log_buffer.append(text)
            asyncio.run_coroutine_threadsafe(q.put(item), main_loop)

        elif item.get("type") == "done":
            # Save consolidated log to file BEFORE sending the DONE signal
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = _report_path(timestamp)
            try:
                with report_path.open("w", encoding="utf-8") as f:
                    f.write(f"=== RAPPORT SSH MASS ({timestamp}) ===\n")
                    f.write(f"Cibles: {len(ips)} équipement(s)\n")
                    f.write("=" * 50 + "\n\n")
                    f.write("\n".join(log_buffer))
                    f.write("\n\n" + "=" * 50 + "\n=== FIN DU RAPPORT ===")

                report_item = {"type": "report_ready", "file": report_path.name}
                asyncio.run_coroutine_threadsafe(q.put(report_item), main_loop)
            except Exception as e:
                error_item = {"type": "log", "text": f"Erreur génération rapport SSH: {e}", "tag": "error"}
                asyncio.run_coroutine_threadsafe(q.put(error_item), main_loop)

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
    raise HTTPException(status_code=404, detail="Task not found")

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
