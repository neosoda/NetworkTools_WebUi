
import sqlite3
import os
import logging

DB_FILE = "network_tools.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        network TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        host_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'running'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS scan_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id INTEGER NOT NULL,
        ip TEXT,
        snmp_version TEXT,
        mac TEXT,
        name TEXT,
        model TEXT,
        description TEXT,
        location TEXT,
        timestamp TEXT,
        FOREIGN KEY (scan_id) REFERENCES scans(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        hostname TEXT,
        status TEXT,
        zip_file TEXT,
        timestamp TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS audit_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        ip TEXT NOT NULL,
        rule_name TEXT,
        status TEXT,
        detail TEXT,
        timestamp TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS config_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT NOT NULL,
        hostname TEXT,
        content TEXT,
        timestamp TEXT NOT NULL
    )''')

    # Topology links
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topology_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_ip TEXT,
            target_ip TEXT,
            source_port TEXT,
            target_port TEXT,
            link_type TEXT,
            timestamp DATETIME
        )
    """)
    
    conn.commit()

    c.execute('''CREATE TABLE IF NOT EXISTS scheduled_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        task_type TEXT NOT NULL,
        cron_expr TEXT NOT NULL,
        params TEXT,
        enabled INTEGER DEFAULT 1,
        last_run TEXT,
        next_run TEXT
    )''')

    conn.commit()
    conn.close()
    logging.info("Database initialized.")
