import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import VersionSummaryResponse, WorkspaceResponse
from app.services.version_service import get_published_version, list_versions
from app.services.workspace_service import build_workspace


router = APIRouter(prefix="/projects/{project_id}", tags=["workspace"])


@router.get("/workspace", response_model=WorkspaceResponse)
def workspace_endpoint(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return build_workspace(db, project_id)


@router.get("/versions", response_model=list[VersionSummaryResponse])
def versions_endpoint(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return list_versions(db, project_id)


@router.get("/versions/{version_id}", response_model=WorkspaceResponse)
def version_endpoint(project_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)):
    get_published_version(db, version_id)
    return build_workspace(db, project_id, version_id=version_id)

