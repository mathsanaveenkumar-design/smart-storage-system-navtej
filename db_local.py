import sqlite3
import json
import os
from config import OFFLINE_DB_PATH

def init_local_db():
    os.makedirs("offline_data", exist_ok=True)
    conn = sqlite3.connect(OFFLINE_DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS offline_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_action_id TEXT UNIQUE,
            action_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            synced INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def add_offline_action(client_action_id, action_type, payload: dict):
    conn = sqlite3.connect(OFFLINE_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO offline_queue (client_action_id, action_type, payload, synced)
        VALUES (?, ?, ?, 0)
    """, (client_action_id, action_type, json.dumps(payload)))
    conn.commit()
    conn.close()

def get_pending_actions():
    conn = sqlite3.connect(OFFLINE_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, client_action_id, action_type, payload
        FROM offline_queue
        WHERE synced = 0
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def mark_action_synced(row_id):
    conn = sqlite3.connect(OFFLINE_DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE offline_queue SET synced = 1 WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()
