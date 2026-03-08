

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.db.database import init_db
from server.scheduler import start_scheduler, shutdown_scheduler
from server.api import scan, backup, ssh_cmd, audit, diff, history, topology, scheduler_api, playbook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global asyncio queue for inter-thread communication
main_queue = asyncio.Queue()

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

# Serve static web files
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/", include_in_schema=False)
async def root():
    index_path = os.path.join(WEB_DIR, "index.html")
    return FileResponse(index_path)

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    import os
    path = os.path.join(os.getcwd(), filename)
    if os.path.exists(path):
        return FileResponse(path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=filename)
    return {"error": "File not found"}

# SPA Catch-all
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_path = os.path.join(WEB_DIR, "index.html")
    return FileResponse(index_path)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}
