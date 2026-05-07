import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ExportType, JobStatus, ScopeType
from app.schemas import JobResponse
from app.services.export_service import create_export_job
from app.services.generation_service import create_initial_candidate, create_regeneration_candidate
from app.services.project_service import get_project
from app.services.validation_service import validate_candidate
from app.services.version_service import publish_candidate


JOBS: dict[uuid.UUID, JobResponse] = {}


def _job_error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            message = detail.get("message")
            if isinstance(message, str):
                return message
        if isinstance(detail, str):
            return detail
    return str(exc)


async def run_generation(db: Session, project_id: uuid.UUID) -> JobResponse:
    job_id = uuid.uuid4()
    JOBS[job_id] = JobResponse(job_id=job_id, status=JobStatus.RUNNING, message="Generation running")
    try:
        project = get_project(db, project_id)
        candidate = await create_initial_candidate(db, project)
        report = validate_candidate(db, candidate)
        if report.overall_status != "pass":
            db.commit()
            response = JobResponse(
                job_id=job_id,
                status=JobStatus.FAILED,
                message="Validation failed; draft was not published",
                candidate_version_id=candidate.candidate_version_id,
            )
        else:
            version = publish_candidate(db, candidate.candidate_version_id)
            response = JobResponse(
                job_id=job_id,
                status=JobStatus.SUCCEEDED,
                message="Generated, validated, and published latest version",
                candidate_version_id=candidate.candidate_version_id,
                version_id=version.version_id,
            )
    except Exception as exc:
        db.rollback()
        response = JobResponse(job_id=job_id, status=JobStatus.FAILED, message=_job_error_message(exc))
    JOBS[job_id] = response
    return response


async def run_regeneration(
    db: Session,
    project_id: uuid.UUID,
    *,
    parent_version_id: uuid.UUID,
    scope_type: ScopeType,
    selected_section: str | None,
    change_instruction: str,
    excluded_source_categories: list[str],
    excluded_document_ids: list[str],
) -> JobResponse:
    job_id = uuid.uuid4()
    JOBS[job_id] = JobResponse(job_id=job_id, status=JobStatus.RUNNING, message="Regeneration running")
    try:
        project = get_project(db, project_id)
        candidate = await create_regeneration_candidate(
            db,
            project,
            parent_version_id=parent_version_id,
            scope_type=scope_type,
            selected_section=selected_section,
            change_instruction=change_instruction,
            excluded_source_categories=excluded_source_categories,
            excluded_document_ids=excluded_document_ids,
        )
        report = validate_candidate(db, candidate)
        if report.overall_status != "pass":
            db.commit()
            response = JobResponse(
                job_id=job_id,
                status=JobStatus.FAILED,
                message="Validation failed; regenerated draft was not published",
                candidate_version_id=candidate.candidate_version_id,
            )
        else:
            version = publish_candidate(db, candidate.candidate_version_id)
            response = JobResponse(
                job_id=job_id,
                status=JobStatus.SUCCEEDED,
                message="Regenerated, validated, and published latest version",
                candidate_version_id=candidate.candidate_version_id,
                version_id=version.version_id,
            )
    except Exception as exc:
        db.rollback()
        response = JobResponse(job_id=job_id, status=JobStatus.FAILED, message=_job_error_message(exc))
    JOBS[job_id] = response
    return response


def get_job(job_id: uuid.UUID) -> JobResponse:
    return JOBS.get(
        job_id,
        JobResponse(job_id=job_id, status=JobStatus.FAILED, message="Job not found in local runner"),
    )


def run_export(db: Session, version_id: uuid.UUID, export_type: ExportType) -> JobResponse:
    job = create_export_job(db, version_id, export_type)
    return JobResponse(
        job_id=uuid.uuid4(),
        status=job.status,
        message=f"{export_type.value} export {job.status.value.lower()}",
        export_job_id=job.export_job_id,
        version_id=version_id,
    )
