"""Database package initialization."""
from app.database.database import init_db, get_db, get_db_session, engine, SessionLocal
from app.database.models import Incident, Alert, AuditLog, IncidentStatus, IncidentSeverity, AlertStatus, Base
from app.database.crud import (
    create_incident,
    get_incident,
    get_incidents,
    count_incidents,
    acknowledge_incident,
    resolve_incident,
    create_alert,
    update_alert_status,
    get_alerts_for_incident,
    get_audit_logs,
    get_incident_stats,
    calculate_severity,
)

__all__ = [
    "init_db",
    "get_db",
    "get_db_session",
    "engine",
    "SessionLocal",
    "Incident",
    "Alert",
    "AuditLog",
    "IncidentStatus",
    "IncidentSeverity",
    "AlertStatus",
    "Base",
    "create_incident",
    "get_incident",
    "get_incidents",
    "count_incidents",
    "acknowledge_incident",
    "resolve_incident",
    "create_alert",
    "update_alert_status",
    "get_alerts_for_incident",
    "get_audit_logs",
    "get_incident_stats",
    "calculate_severity",
]