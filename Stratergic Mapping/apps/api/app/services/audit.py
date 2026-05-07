import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit(
    db: Session,
    action_type: str,
    *,
    project_id: uuid.UUID | None = None,
    version_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    audit = AuditLog(
        project_id=project_id,
        version_id=version_id,
        action_type=action_type,
        payload_json=payload or {},
    )
    db.add(audit)
    return audit

