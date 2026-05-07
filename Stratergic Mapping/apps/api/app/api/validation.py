import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import ValidationReportResponse, VersionSummaryResponse
from app.services.validation_service import get_validation_report, validate_candidate
from app.services.version_service import get_candidate, publish_candidate


router = APIRouter(prefix="/candidate-versions/{candidate_version_id}", tags=["validation"])


@router.post("/validate", response_model=ValidationReportResponse)
def validate_candidate_endpoint(candidate_version_id: uuid.UUID, db: Session = Depends(get_db)):
    candidate = get_candidate(db, candidate_version_id)
    report = validate_candidate(db, candidate)
    db.commit()
    db.refresh(report)
    return report


@router.get("/validation", response_model=ValidationReportResponse)
def get_validation_endpoint(candidate_version_id: uuid.UUID, db: Session = Depends(get_db)):
    report = get_validation_report(db, candidate_version_id)
    if not report:
        raise HTTPException(status_code=404, detail="Validation report not found")
    return report


@router.post("/publish", response_model=VersionSummaryResponse)
def publish_candidate_endpoint(candidate_version_id: uuid.UUID, db: Session = Depends(get_db)):
    return publish_candidate(db, candidate_version_id)

