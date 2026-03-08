import json
from datetime import datetime
from fastapi import APIRouter
from server.db.database import get_db
from server.scheduler import add_job_to_engine, remove_job_from_engine

router = APIRouter()

@router.get("/tasks")
async def get_tasks():
    conn = get_db()
    rows = conn.execute("SELECT * FROM scheduled_tasks ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/tasks")
async def create_task(body: dict):
    name = body.get("name")
    task_type = body.get("task_type")
    cron_expr = body.get("cron_expr")
    params = json.dumps(body.get("params", {}))
    
    conn = get_db()
    conn.execute(
        "INSERT INTO scheduled_tasks (name, task_type, cron_expr, params, enabled) VALUES (?,?,?,?,1)",
        (name, task_type, cron_expr, params)
    )
    conn.commit()
    task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    
    # Sync with engine
    add_job_to_engine(task_id, task_type, cron_expr, params)
    
    return {"id": task_id, "status": "created"}

@router.put("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM scheduled_tasks WHERE id=?", (task_id,)).fetchone()
    if row:
        new_state = 0 if row["enabled"] else 1
        conn.execute("UPDATE scheduled_tasks SET enabled=? WHERE id=?", (new_state, task_id))
        conn.commit()
        
        if new_state:
            add_job_to_engine(task_id, row['task_type'], row['cron_expr'], row['params'])
        else:
            remove_job_from_engine(task_id)
            
    conn.close()
    return {"status": "toggled"}

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    conn = get_db()
    conn.execute("DELETE FROM scheduled_tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    
    remove_job_from_engine(task_id)
    return {"status": "deleted"}
