import logging
import json
import uuid
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from server.db.database import DB_FILE, get_db

# Late imports to avoid circular dependencies locally in the handlers
# Though for clean code we generally want them hoisted, circular dependency is an issue if models are cyclic.
# We will pull them up to the top and ensure they don't break.
from server.api.scan import _run_scan, _active_scans

logger = logging.getLogger(__name__)

# Storage for jobs so they survive restart
job_stores = {
    'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_FILE}')
}

scheduler = AsyncIOScheduler(jobstores=job_stores)

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started with SQLite job store.")
        sync_all_jobs()

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shut down.")

def sync_all_jobs():
    """Load enabled jobs from DB and add them to scheduler"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM scheduled_tasks WHERE enabled=1").fetchall()
    conn.close()
    
    for row in rows:
        add_job_to_engine(row['id'], row['task_type'], row['cron_expr'], row['params'])

def add_job_to_engine(task_id, task_type, cron_expr, params=None):
    job_id = f"job_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    
    # Map task_type to function
    func = None
    if task_type == 'scan':
        func = run_scheduled_scan
        args = [json.loads(params).get('network', '192.168.1.0/24')] if params else ['192.168.1.0/24']
    
    if func:
        # cron_expr format check
        try:
            # We assume cron_expr is standard cron like "0 6 * * 1"
            # APScheduler cron trigger needs: minute, hour, day, month, day_of_week
            parts = cron_expr.split()
            if len(parts) == 5:
                scheduler.add_job(func, 'cron', 
                                  minute=parts[0], hour=parts[1], 
                                  day=parts[2], month=parts[3], 
                                  day_of_week=parts[4],
                                  id=job_id, args=args)
                logger.info(f"Job {job_id} added/updated.")
        except Exception as e:
            logger.error(f"Error adding job {job_id}: {e}")

def remove_job_from_engine(task_id):
    job_id = f"job_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Job {job_id} removed.")

# Task wrappers
async def run_scheduled_scan(network: str):
    logger.info(f"🚀 Running scheduled scan for {network}")
    db_id = None
    try:
        conn = get_db()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO scans (network, started_at, status) VALUES (?, ?, 'running')", (network, ts))
        conn.commit()
        db_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        
        scan_id = str(uuid.uuid4())
        _active_scans[scan_id] = {"queue": asyncio.Queue(), "db_id": db_id}
        
        # This will run in a thread and write results to DB
        _run_scan(scan_id, db_id, network)
        logger.info(f"✅ Scheduled scan {db_id} triggered.")
    except Exception as e:
        logger.error(f"❌ Error in scheduled scan: {e}")
