from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from db.session import Base
import uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


def log_action(
    db: Session,
    action: str,
    user_id: str = None,
    resource: str = None,
    ip_address: str = None,
    details: str = None,
):
    entry = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        resource=resource,
        ip_address=ip_address,
        details=details,
    )
    db.add(entry)
    db.commit()
