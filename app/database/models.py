"""SQLAlchemy models for incidents, alerts, and audit log."""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    Enum,
    Index,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class IncidentStatus(str, PyEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class IncidentSeverity(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Incident(Base):
    """Fire/smoke incident record."""
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(String(64), nullable=False, index=True)
    camera_name = Column(String(128))
    
    # Detection details
    confidence = Column(Float, nullable=False)
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)
    class_name = Column(String(32))  # "fire" or "smoke"
    
    # Severity & status
    severity = Column(Enum(IncidentSeverity), default=IncidentSeverity.MEDIUM, nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, nullable=False, index=True)
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # User actions
    acknowledged_by = Column(String(64), nullable=True)
    resolved_by = Column(String(64), nullable=True)
    
    # Snapshot
    snapshot_path = Column(String(512), nullable=True)
    
    # Metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for extensibility
    
    # Relationships
    alerts = relationship("Alert", back_populates="incident", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="incident", cascade="all, delete-orphan")

    # Composite indexes
    __table_args__ = (
        Index("ix_incidents_camera_status", "camera_id", "status"),
        Index("ix_incidents_detected_status", "detected_at", "status"),
    )


class Alert(Base):
    """Alert notification record."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    provider = Column(String(32), nullable=False)  # "email", "telegram", "webhook"
    status = Column(Enum(AlertStatus), default=AlertStatus.PENDING, nullable=False)
    
    recipient = Column(String(256))  # email, chat_id, or webhook URL
    subject = Column(String(256))
    message = Column(Text)
    
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    incident = relationship("Incident", back_populates="alerts")


class AuditLog(Base):
    """Audit trail for incident lifecycle actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    action = Column(String(64), nullable=False)  # "created", "acknowledged", "resolved", "status_changed"
    performed_by = Column(String(64), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    incident = relationship("Incident", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_incident_timestamp", "incident_id", "timestamp"),
    )


class UserRole(str, PyEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(Base):
    """User account for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)