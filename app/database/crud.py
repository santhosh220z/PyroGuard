"""CRUD operations for incidents, alerts, and audit logs."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_

from app.database.models import Incident, Alert, AuditLog, IncidentStatus, IncidentSeverity, AlertStatus, AlertProfile


def calculate_severity(confidence: float, class_name: str) -> IncidentSeverity:
    """Calculate incident severity based on confidence and class."""
    if class_name == "fire":
        if confidence >= 0.85:
            return IncidentSeverity.CRITICAL
        elif confidence >= 0.7:
            return IncidentSeverity.HIGH
        elif confidence >= 0.5:
            return IncidentSeverity.MEDIUM
        return IncidentSeverity.LOW
    else:  # smoke
        if confidence >= 0.9:
            return IncidentSeverity.HIGH
        elif confidence >= 0.7:
            return IncidentSeverity.MEDIUM
        return IncidentSeverity.LOW


def get_alert_profile(db: Session) -> Optional[AlertProfile]:
    """Get the singleton alert-contact profile (id=1), or None if unset."""
    return db.query(AlertProfile).filter(AlertProfile.id == 1).first()


def save_alert_profile(
    db: Session,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    notify_email: bool = True,
    phone: Optional[str] = None,
    notify_sms: bool = False,
    telegram_chat_id: Optional[str] = None,
    notify_telegram: bool = False,
    pin_hash: Optional[str] = None,
    resend_api_key_enc: Optional[str] = None,
    resend_from: Optional[str] = None,
) -> AlertProfile:
    """Create or update the singleton alert-contact profile (id=1)."""
    profile = db.query(AlertProfile).filter(AlertProfile.id == 1).first()
    if profile is None:
        profile = AlertProfile(id=1)
        db.add(profile)
    profile.display_name = display_name or None
    profile.email = email or None
    profile.notify_email = bool(notify_email)
    profile.phone = phone or None
    profile.notify_sms = bool(notify_sms)
    profile.telegram_chat_id = telegram_chat_id or None
    profile.notify_telegram = bool(notify_telegram)
    if resend_api_key_enc is not None:
        profile.resend_api_key_hash = resend_api_key_enc or None
    if resend_from is not None:
        profile.resend_from = resend_from or None
    if pin_hash is not None:
        profile.pin_hash = pin_hash
    profile.updated_at = datetime.utcnow()
    db.flush()
    return profile


def create_incident(
    db: Session,
    camera_id: str,
    camera_name: str,
    confidence: float,
    bbox: Dict[str, float],
    class_name: str,
    snapshot_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Incident:
    """Create a new incident record."""
    severity = calculate_severity(confidence, class_name)
    
    incident = Incident(
        camera_id=camera_id,
        camera_name=camera_name,
        confidence=confidence,
        bbox_x1=bbox.get("x1"),
        bbox_y1=bbox.get("y1"),
        bbox_x2=bbox.get("x2"),
        bbox_y2=bbox.get("y2"),
        class_name=class_name,
        severity=severity,
        status=IncidentStatus.OPEN,
        snapshot_path=snapshot_path,
        metadata_json=str(metadata) if metadata else None,
    )
    db.add(incident)
    db.flush()
    
    # Audit log
    audit = AuditLog(
        incident_id=incident.id,
        action="created",
        performed_by="system",
        new_value=f"severity={severity.value}, confidence={confidence:.2f}",
    )
    db.add(audit)
    
    return incident


def get_incident(db: Session, incident_id: int) -> Optional[Incident]:
    """Get incident by ID with relationships loaded."""
    return db.query(Incident).filter(Incident.id == incident_id).first()


def get_incidents(
    db: Session,
    status: Optional[IncidentStatus] = None,
    camera_id: Optional[str] = None,
    severity: Optional[IncidentSeverity] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Incident]:
    """Get incidents with filtering and pagination."""
    query = db.query(Incident)
    
    if status:
        query = query.filter(Incident.status == status)
    if camera_id:
        query = query.filter(Incident.camera_id == camera_id)
    if severity:
        query = query.filter(Incident.severity == severity)
    if start_date:
        query = query.filter(Incident.detected_at >= start_date)
    if end_date:
        query = query.filter(Incident.detected_at <= end_date)
    
    return query.order_by(desc(Incident.detected_at)).limit(limit).offset(offset).all()


def count_incidents(
    db: Session,
    status: Optional[IncidentStatus] = None,
    camera_id: Optional[str] = None,
) -> int:
    """Count incidents matching filters."""
    query = db.query(func.count(Incident.id))
    if status:
        query = query.filter(Incident.status == status)
    if camera_id:
        query = query.filter(Incident.camera_id == camera_id)
    return query.scalar() or 0


def acknowledge_incident(
    db: Session,
    incident_id: int,
    user: str,
) -> Optional[Incident]:
    """Acknowledge an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        return None
    
    old_status = incident.status.value
    incident.status = IncidentStatus.ACKNOWLEDGED
    incident.acknowledged_at = datetime.utcnow()
    incident.acknowledged_by = user
    
    # Audit log
    audit = AuditLog(
        incident_id=incident.id,
        action="acknowledged",
        performed_by=user,
        old_value=old_status,
        new_value=incident.status.value,
    )
    db.add(audit)
    
    return incident


def resolve_incident(
    db: Session,
    incident_id: int,
    user: str,
    mark_false_positive: bool = False,
) -> Optional[Incident]:
    """Resolve an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        return None
    
    old_status = incident.status.value
    incident.status = IncidentStatus.FALSE_POSITIVE if mark_false_positive else IncidentStatus.RESOLVED
    incident.resolved_at = datetime.utcnow()
    incident.resolved_by = user
    
    # Audit log
    audit = AuditLog(
        incident_id=incident.id,
        action="resolved" if not mark_false_positive else "marked_false_positive",
        performed_by=user,
        old_value=old_status,
        new_value=incident.status.value,
    )
    db.add(audit)
    
    return incident


def create_alert(
    db: Session,
    incident_id: int,
    provider: str,
    recipient: str,
    subject: str,
    message: str,
) -> Alert:
    """Create an alert record."""
    alert = Alert(
        incident_id=incident_id,
        provider=provider,
        recipient=recipient,
        subject=subject,
        message=message,
        status=AlertStatus.PENDING,
    )
    db.add(alert)
    return alert


def update_alert_status(
    db: Session,
    alert_id: int,
    status: AlertStatus,
    error_message: Optional[str] = None,
) -> Optional[Alert]:
    """Update alert status."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None
    
    alert.status = status
    if error_message:
        alert.error_message = error_message
        alert.retry_count += 1
    if status == AlertStatus.SENT:
        alert.sent_at = datetime.utcnow()
    
    return alert


def get_alerts_for_incident(db: Session, incident_id: int) -> List[Alert]:
    """Get all alerts for an incident."""
    return db.query(Alert).filter(Alert.incident_id == incident_id).all()


def get_audit_logs(db: Session, incident_id: int) -> List[AuditLog]:
    """Get audit logs for an incident."""
    return db.query(AuditLog).filter(AuditLog.incident_id == incident_id).order_by(AuditLog.timestamp).all()


def get_incident_stats(db: Session) -> Dict[str, Any]:
    """Get incident statistics for dashboard."""
    total = db.query(func.count(Incident.id)).scalar() or 0
    open_count = db.query(func.count(Incident.id)).filter(Incident.status == IncidentStatus.OPEN).scalar() or 0
    acked_count = db.query(func.count(Incident.id)).filter(Incident.status == IncidentStatus.ACKNOWLEDGED).scalar() or 0
    resolved_count = db.query(func.count(Incident.id)).filter(Incident.status == IncidentStatus.RESOLVED).scalar() or 0
    fp_count = db.query(func.count(Incident.id)).filter(Incident.status == IncidentStatus.FALSE_POSITIVE).scalar() or 0
    
    # Last 24h
    from datetime import timedelta
    day_ago = datetime.utcnow() - timedelta(days=1)
    last_24h = db.query(func.count(Incident.id)).filter(Incident.detected_at >= day_ago).scalar() or 0
    
    return {
        "total": total,
        "open": open_count,
        "acknowledged": acked_count,
        "resolved": resolved_count,
        "false_positive": fp_count,
        "last_24h": last_24h,
    }