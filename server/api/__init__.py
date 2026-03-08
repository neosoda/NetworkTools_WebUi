
import asyncio
import json
import threading
import uuid
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
import re
from server.db.database import get_db

router = APIRouter()

_active_scans = {}
_active_backups = {}

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"settings": {"snmp_communities": ["public"], "ip_scan_limit_last_octet": 254}, "oids": {}}
