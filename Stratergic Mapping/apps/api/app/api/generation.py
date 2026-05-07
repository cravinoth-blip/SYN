import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ScopeType
from app.schemas import (
    GenerateProjectRequest,
    JobResponse,
    RegenerateFullRequest,
    RegenerateSectionRequest,
)
from app.services.orchestrator import get_job, run_generation, run_regeneration


router = APIRouter(prefix="/projects/{project_id}", tags=["generation"])


@router.post("/generate", response_model=JobResponse)
async def generate_endpoint(
    project_id: uuid.UUID, _payload: GenerateProjectRequest | None = None, db: Session = Depends(get_db)
):
    return await run_generation(db, project_id)


@router.get("/generate/{job_id}", response_model=JobResponse)
def get_generation_job_endpoint(project_id: uuid.UUID, job_id: uuid.UUID):
    return get_job(job_id)


@router.post("/regenerate/full", response_model=JobResponse)
async def regenerate_full_endpoint(
    project_id: uuid.UUID, payload: RegenerateFullRequest, db: Session = Depends(get_db)
):
    return await run_regeneration(
        db,
        project_id,
        parent_version_id=payload.parent_version_id,
        scope_type=ScopeType.FULL,
        selected_section=None,
        change_instruction=payload.change_instruction,
        excluded_source_categories=payload.excluded_source_categories,
        excluded_document_ids=payload.excluded_document_ids,
    )


@router.post("/regenerate/section", response_model=JobResponse)
async def regenerate_section_endpoint(
    project_id: uuid.UUID, payload: RegenerateSectionRequest, db: Session = Depends(get_db)
):
    return await run_regeneration(
        db,
        project_id,
        parent_version_id=payload.parent_version_id,
        scope_type=ScopeType.SECTION,
        selected_section=payload.section_name,
        change_instruction=payload.change_instruction,
        excluded_source_categories=payload.excluded_source_categories,
        excluded_document_ids=payload.excluded_document_ids,
    )

