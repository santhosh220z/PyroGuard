# PyroGuard Incidents Module
# Incident database and evidence management

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

class IncidentDatabase:
    """SQLite-based incident database."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "data/incidents/incidents.db"
        self.db_path = str(Path(self.db_path).resolve())
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                confidence REAL,
                status TEXT NOT NULL DEFAULT 'DETECTED',
                snapshot_path TEXT,
                notification_status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT,
                event_type TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                details TEXT,
                FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_incident(self, incident_id: str, timestamp: str, camera_id: str,
                        event_type: str, confidence: float = None,
                        snapshot_path: str = None) -> dict:
        """Create a new incident record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO incidents (incident_id, timestamp, camera_id, event_type, confidence, snapshot_path, notification_status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            ''', (incident_id, timestamp, camera_id, event_type, confidence, snapshot_path))
            
            incident_id_db = incident_id
            conn.commit()
            
            # Return incident record
            cursor.execute('SELECT * FROM incidents WHERE incident_id = ?', (incident_id,))
            row = cursor.fetchone()
            columns = [desc[0] for desc in cursor.description]
            incident_dict = dict(zip(columns, row))
            
            return incident_dict
        except sqlite3.IntegrityError:
            return {"error": f"Incident {incident_id} already exists"}
        finally:
            conn.close()
    
    def get_incident(self, incident_id: str) -> dict:
        """Get incident by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM incidents WHERE incident_id = ?', (incident_id,))
        row = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row)) if row else {"error": "incident not found"}
        conn.close()
        return result
    
    def update_status(self, incident_id: str, status: str) -> bool:
        """Update incident status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('UPDATE incidents SET status = ? WHERE incident_id = ?', (status, incident_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
        finally:
            conn.close()
    
    def list_incidents(self, status: str = None) -> list:
        """List incidents, optionally filtered by status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT incident_id, timestamp, camera_id, event_type, status, created_at FROM incidents WHERE status = ? ORDER BY created_at DESC', (status,))
        else:
            cursor.execute('SELECT incident_id, timestamp, camera_id, event_type, status, created_at FROM incidents ORDER BY created_at DESC')
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return result