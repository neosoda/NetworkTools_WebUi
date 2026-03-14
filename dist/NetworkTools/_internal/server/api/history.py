
from fastapi import APIRouter
from server.db.database import get_db

router = APIRouter()

@router.get("/scans")
async def get_scan_history():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, network, started_at, finished_at, host_count, status FROM scans ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/scans/{scan_id}/results")
async def get_scan_results(scan_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT ip, snmp_version, mac, name, model, description, location, timestamp FROM scan_results WHERE scan_id=? ORDER BY ip",
        (scan_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/audits")
async def get_audit_history():
    conn = get_db()
    rows = conn.execute(
        """SELECT session_id, ip, rule_name, status, detail, timestamp 
           FROM audit_results ORDER BY timestamp DESC LIMIT 500"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/audits/summary")
async def get_audit_summary():
    conn = get_db()
    rows = conn.execute(
        """SELECT timestamp, 
           COUNT(CASE WHEN status='Conforme' THEN 1 END) as ok,
           COUNT(CASE WHEN status='Non Conforme' THEN 1 END) as nok
           FROM audit_results 
           GROUP BY date(timestamp) 
           ORDER BY timestamp DESC LIMIT 30"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/backups")
async def get_backup_history():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, ip, hostname, status, zip_file, timestamp FROM backups ORDER BY timestamp DESC LIMIT 500"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
