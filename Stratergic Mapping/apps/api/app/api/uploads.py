import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import UploadResponse
from app.services.upload_service import delete_project_file, list_project_files, upload_project_file


router = APIRouter(prefix="/projects/{project_id}/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse)
async def upload_endpoint(
    project_id: uuid.UUID, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    return await upload_project_file(db, project_id, file)


@router.get("", response_model=list[UploadResponse])
def list_uploads_endpoint(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return list_project_files(db, project_id)


@router.delete("/{file_id}", status_code=204)
def delete_upload_endpoint(project_id: uuid.UUID, file_id: uuid.UUID, db: Session = Depends(get_db)):
    delete_project_file(db, project_id, file_id)

