
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.db.database import init_db
from server.scheduler import start_scheduler, shutdown_scheduler
from server.api import scan, backup, ssh_cmd, audit, diff, history, topology, scheduler_api, playbook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global asyncio queue for inter-thread communication
main_queue = asyncio.Queue()


def _safe_download_path(filename: str) -> Path:
    """Resolve and validate download file path to prevent path traversal."""
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    from server.utils.paths import get_app_data_dir

    app_data_dir = Path(get_app_data_dir()).resolve()
    requested_path = (app_data_dir / filename).resolve()
    if requested_path.parent != app_data_dir:
        raise HTTPException(status_code=400, detail="Invalid filename")

    return requested_path

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown handler"""
    logger.info("Network Tools V3 Server Starting...")
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Server shutting down.")

app = FastAPI(
    title="Network Tools V3",
    description="Outil de gestion réseau professionnel",
    version="3.0.0",
    lifespan=lifespan,
)

# Include API routers
app.include_router(scan.router, prefix="/api/scan", tags=["SNMP Scan"])
app.include_router(backup.router, prefix="/api/backup", tags=["Backup"])
app.include_router(ssh_cmd.router, prefix="/api/ssh", tags=["SSH"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(diff.router, prefix="/api/diff", tags=["Diff"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(topology.router, prefix="/api/topology", tags=["Topology"])
app.include_router(scheduler_api.router, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(playbook.router, prefix="/api/playbook", tags=["Playbooks"])

# Serve static web files
from server.utils.paths import get_bundle_resource_path
WEB_DIR = get_bundle_resource_path("web")

if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/", include_in_schema=False)
async def root():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": f"Fichiers Web non trouvés dans {WEB_DIR}"}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    import mimetypes
    from server.utils.paths import get_app_data_dir

    requested_path = _safe_download_path(filename)

    # Fallback to current working directory for local development compatibility
    local_fallback_path = Path(os.getcwd()).resolve() / Path(filename).name
    candidate_paths = [requested_path, local_fallback_path]

    for path in candidate_paths:
        if path.exists() and path.is_file():
            # Restrict fallback file serving to files inside current app data dir or cwd.
            app_data_dir = Path(get_app_data_dir()).resolve()
            cwd = Path(os.getcwd()).resolve()
            if app_data_dir not in path.parents and cwd not in path.parents:
                raise HTTPException(status_code=403, detail="Unauthorized file access")

            mt, _ = mimetypes.guess_type(str(path))
        # Only set 'filename' for attachment, but we want inline viewing for HTML
            headers = {}
            if not filename.endswith('.html'):
                headers["Content-Disposition"] = f'attachment; filename="{filename}"'

            return FileResponse(
                str(path),
                media_type=mt or 'application/octet-stream',
                headers=headers,
            )

    raise HTTPException(status_code=404, detail="File not found")

# SPA Catch-all
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Fichiers Web non trouvés"}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}
