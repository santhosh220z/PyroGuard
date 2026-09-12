"""PyroGuard Unit Tests - Database Module"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import tempfile
import os

from app.database.incident_db import IncidentDatabase


def test_incident_creation():
    """Test creating an incident record."""
    # Use a temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = IncidentDatabase(db_path=db_path)
        
        # Create incident
        incident = db.create_incident(
            incident_id="test_001",
            timestamp="2024-01-01T12:00:00",
            camera_id="camera_01",
            event_type="fire",
            confidence=0.95,
            snapshot_path="/tmp/snapshot.jpg"
        )
        
        assert "incident_id" in incident or "error" not in incident, "Incident should be created"
        assert incident.get("incident_id") == "test_001", "incident_id should match"
        assert incident.get("status") == "DETECTED", "Status should be DETECTED"
        assert incident.get("notification_status") == "pending", "notification_status should be pending"
        
        print("✅ test_incident_creation: PASSED")
        
        # Retrieve incident
        retrieved = db.get_incident("test_001")
        assert retrieved.get("incident_id") == "test_001"
        print("✅ test_incident_retrieval: PASSED")
        
        # Update status
        updated = db.update_status("test_001", "CONFIRMED")
        assert updated, "Status update should succeed"
        
        retrieved = db.get_incident("test_001")
        assert retrieved.get("status") == "CONFIRMED"
        print("✅ test_incident_status_changes: PASSED")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_incident_statuses():
    """Test all incident statuses are valid."""
    valid_statuses = ["DETECTED", "CONFIRMED", "ALERT_SENT", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"]
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = IncidentDatabase(db_path=db_path)
        
        # Create incident
        db.create_incident(
            incident_id="status_test",
            timestamp="2024-01-01T12:00:00",
            camera_id="camera_01",
            event_type="fire",
            confidence=0.9
        )
        
        # Test all statuses
        for status in valid_statuses:
            updated = db.update_status("status_test", status)
            assert updated, f"Should be able to update status to {status}"
            
            retrieved = db.get_incident("status_test")
            assert retrieved.get("status") == status, f"Status should be {status}"
        
        print(f"✅ test_incident_statuses: PASSED (all {len(valid_statuses)} statuses)")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_incident_list():
    """Test listing incidents."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = IncidentDatabase(db_path=db_path)
        
        # Create a few incidents
        for i in range(3):
            db.create_incident(
                incident_id=f"list_test_{i}",
                timestamp=f"2024-01-0{i}T12:00:00",
                camera_id="camera_01",
                event_type="fire",
                confidence=0.9
            )
        
        # List all
        all_incidents = db.list_incidents()
        assert len(all_incidents) >= 3, f"Should have at least 3 incidents, got {len(all_incidents)}"
        
        # List by status
        detected = db.list_incidents(status="DETECTED")
        assert len(detected) >= 1
        
        print("✅ test_incident_list: PASSED")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)