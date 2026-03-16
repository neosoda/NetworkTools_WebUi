import asyncio
import json
import queue
import threading
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()
_active_playbooks: dict[str, asyncio.Queue[dict[str, Any]]] = {}
PLAYBOOKS_DIR = Path("playbooks")
PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)


class RunPlaybookRequest(BaseModel):
    filename: str
    ips: list[str] = Field(default_factory=list)
    username: str = ""
    password: str = ""


def _resolve_playbook_path(filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise ValueError("Invalid playbook filename")
    path = (PLAYBOOKS_DIR / filename).resolve()
    if path.parent != PLAYBOOKS_DIR.resolve():
        raise ValueError("Invalid playbook filename")
    return path


@router.get("/")
async def list_playbooks() -> list[dict[str, str]]:
    files = [p.name for p in PLAYBOOKS_DIR.iterdir() if p.is_file() and p.suffix in {".yaml", ".yml"}]
    playbooks: list[dict[str, str]] = []
    for filename in files:
        try:
            with (PLAYBOOKS_DIR / filename).open("r", encoding="utf-8") as stream:
                content = yaml.safe_load(stream)
                if not isinstance(content, dict):
                    raise ValueError("Invalid YAML root")
                playbooks.append(
                    {
                        "filename": filename,
                        "name": str(content.get("name", filename)),
                        "description": str(content.get("description", "")),
                    }
                )
        except (OSError, yaml.YAMLError, ValueError):
            playbooks.append({"filename": filename, "name": filename, "error": "Invalid YAML"})
    return playbooks


@router.post("/run")
async def run_playbook(body: RunPlaybookRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    try:
        playbook_path = _resolve_playbook_path(body.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not playbook_path.exists() or not playbook_path.is_file():
        raise HTTPException(status_code=404, detail="Playbook not found")

    task_id = str(uuid.uuid4())
    task_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _active_playbooks[task_id] = task_queue

    background_tasks.add_task(
        _execute_playbook,
        task_id,
        body.filename,
        body.ips,
        body.username,
        body.password,
    )
    return {"task_id": task_id}


async def _execute_playbook(task_id: str, filename: str, ips: list[str], username: str, password: str) -> None:
    task_queue = _active_playbooks[task_id]

    try:
        playbook_path = _resolve_playbook_path(filename)
        with playbook_path.open("r", encoding="utf-8") as stream:
            playbook = yaml.safe_load(stream)

        if not isinstance(playbook, dict):
            raise ValueError("Invalid playbook content")

        await task_queue.put({"type": "log", "text": f"🚀 Démarrage du playbook: {playbook.get('name', filename)}"})

        steps = playbook.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("Invalid playbook steps")

        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                await task_queue.put({"type": "log", "text": f"⚠️ Étape ignorée ({index}): format invalide", "tag": "warning"})
                continue

            await task_queue.put({"type": "log", "text": f"--- Étape {index}: {step.get('name', 'Action')} ---"})

            if "ssh" in step:
                await _run_ssh_step(task_queue, ips, step["ssh"], username, password)
            elif "audit" in step:
                await task_queue.put({"type": "log", "text": "⚠️ Étape audit non implémentée", "tag": "warning"})

        await task_queue.put({"type": "log", "text": "✅ Playbook terminé avec succès."})
    except (OSError, yaml.YAMLError, ValueError) as exc:
        await task_queue.put({"type": "log", "text": f"❌ Erreur playbook: {exc}", "tag": "error"})
    except Exception as exc:
        await task_queue.put({"type": "log", "text": f"❌ Erreur inattendue playbook: {exc}", "tag": "error"})

    await task_queue.put({"type": "done"})


async def _run_ssh_step(
    task_queue: asyncio.Queue[dict[str, Any]],
    ips: list[str],
    commands: list[str] | str,
    username: str,
    password: str,
) -> None:
    if isinstance(commands, str):
        commands = [commands]

    from server.managers.ssh_manager import SSHManager

    manager = SSHManager()
    sync_q: queue.Queue[dict[str, Any]] = queue.Queue()

    worker = threading.Thread(
        target=manager.run_ssh_commands,
        args=(ips, commands, username, password, 10, sync_q),
        daemon=True,
    )
    worker.start()

    while True:
        item = sync_q.get()
        if item.get("type") == "log":
            await task_queue.put(item)
        if item.get("type") == "done":
            break


@router.get("/stream/{task_id}")
async def stream_playbook(task_id: str) -> StreamingResponse:
    async def gen():
        if task_id not in _active_playbooks:
            yield f"data: {json.dumps({'type': 'error', 'text': 'Non trouvé'})}\n\n"
            return
        task_queue = _active_playbooks[task_id]
        while True:
            item = await task_queue.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "done":
                _active_playbooks.pop(task_id, None)
                break

    return StreamingResponse(gen(), media_type="text/event-stream")
