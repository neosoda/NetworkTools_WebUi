
import json
from fastapi import APIRouter
from server.db.database import get_db

router = APIRouter()

@router.get("/map")
async def get_topology():
    """Return network topology nodes and links from DB."""
    nodes = []
    edges = []
    
    conn = get_db()
    
    # Nodes from last scan
    rows = conn.execute(
        """SELECT sr.ip, sr.name, sr.model, sr.description, sr.location,
           (SELECT status FROM audit_results ar WHERE ar.ip=sr.ip ORDER BY ar.timestamp DESC LIMIT 1) as audit_status
           FROM scan_results sr
           JOIN scans s ON sr.scan_id = s.id
           WHERE s.id = (SELECT MAX(id) FROM scans WHERE status='done')"""
    ).fetchall()
    
    # Edges from topology_links
    link_rows = conn.execute("SELECT * FROM topology_links").fetchall()
    conn.close()
    
    for row in rows:
        r = dict(row)
        status = r.get("audit_status") or "unknown"
        color = {"Conforme": "#22c55e", "Non conforme": "#ef4444", "unknown": "#3b82f6"}.get(status, "#3b82f6")
        nodes.append({
            "id": r["ip"],
            "label": r["name"] or r["ip"],
            "title": f"IP: {r['ip']}\nModèle: {r['model']}\nStatut: {status}",
            "color": color,
            "ip": r["ip"],
            "model": r["model"],
            "location": r["location"],
        })
    
    for l in link_rows:
        edges.append({
            "from": l["source_ip"],
            "to": l["target_ip"],
            "label": f"{l['source_port']} -> {l['target_port']}",
            "title": f"Type: {l['link_type']}"
        })
    
    return {"nodes": nodes, "edges": edges}

@router.post("/discover")
async def discover_topology(body: dict):
    """Trigger LLDP discovery on a list of IPs"""
    ips = body.get("ips", [])
    from server.managers.topology_manager import TopologyManager
    tm = TopologyManager()
    
    # In a real scenario, this would be a background task
    # For now, we manually create a few links to test the UI if links are found
    if len(ips) >= 2:
        tm.save_link(ips[0], ips[1], "Gi0/1", "Gi0/2")
        
    return {"status": "discovery_started"}
