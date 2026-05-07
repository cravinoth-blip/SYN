import uuid

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Project, Version
from app.schemas import CreateProjectRequest, UpdateProjectRequest
from app.services.audit import record_audit


REQUIRED_FIELDS = ("project_name", "disease", "geography", "client_name")
REQUIRED_FIELD_REASONS = {
    "project_name": {
        "label": "Project name",
        "reason": "needed to save and reopen the workspace",
    },
    "disease": {
        "label": "Disease",
        "reason": "needed to build the evidence retrieval plan",
    },
    "geography": {
        "label": "Geography",
        "reason": "needed to scope sources and market context",
    },
    "client_name": {
        "label": "Client or account",
        "reason": "needed to tailor the company, customer, and channel analysis",
    },
}


def _generation_blocked_message(missing: list[str]) -> str:
    reasons = [
        f"{REQUIRED_FIELD_REASONS[field]['label']} is {REQUIRED_FIELD_REASONS[field]['reason']}"
        for field in missing
    ]
    return f"Generation blocked: {'; '.join(reasons)}."


def validate_project_scope(project: Project) -> None:
    missing = [field for field in REQUIRED_FIELDS if not (getattr(project, field) or "").strip()]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": _generation_blocked_message(missing),
                "missing_fields": missing,
                "missing_reasons": [
                    {"field": field, **REQUIRED_FIELD_REASONS[field]} for field in missing
                ],
            },
        )


def create_project(db: Session, payload: CreateProjectRequest) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    record_audit(db, "project.created", project_id=project.project_id, payload=payload.model_dump())
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def update_project(db: Session, project_id: uuid.UUID, payload: UpdateProjectRequest) -> Project:
    project = get_project(db, project_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    record_audit(db, "project.updated", project_id=project.project_id, payload=payload.model_dump())
    db.commit()
    db.refresh(project)
    return project


def recent_projects(db: Session, limit: int = 10) -> list[Project]:
    statement = select(Project).order_by(desc(Project.updated_at)).limit(limit)
    return list(db.scalars(statement))


def latest_version_for_project(db: Session, project_id: uuid.UUID) -> Version | None:
    statement = (
        select(Version)
        .where(Version.project_id == project_id, Version.latest_flag.is_(True))
        .order_by(desc(Version.published_at))
        .limit(1)
    )
    return db.scalars(statement).first()
