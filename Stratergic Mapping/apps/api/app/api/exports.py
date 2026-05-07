import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ExportType
from app.schemas import ExportResponse, JobResponse
from app.services.export_service import get_export_job
from app.services.orchestrator import run_export


router = APIRouter(tags=["exports"])


@router.post("/versions/{version_id}/export/pdf", response_model=JobResponse)
def export_pdf_endpoint(version_id: uuid.UUID, db: Session = Depends(get_db)):
    return run_export(db, version_id, ExportType.PDF)


@router.post("/versions/{version_id}/export/pptx", response_model=JobResponse)
def export_pptx_endpoint(version_id: uuid.UUID, db: Session = Depends(get_db)):
    return run_export(db, version_id, ExportType.PPTX)


@router.get("/exports/{export_job_id}", response_model=ExportResponse)
def get_export_endpoint(export_job_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_export_job(db, export_job_id)

