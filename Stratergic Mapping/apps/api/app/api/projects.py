import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import CreateProjectRequest, ProjectResponse, UpdateProjectRequest
from app.services.project_service import create_project, get_project, recent_projects, update_project


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
def create_project_endpoint(payload: CreateProjectRequest, db: Session = Depends(get_db)):
    return create_project(db, payload)


@router.get("/recent", response_model=list[ProjectResponse])
def recent_projects_endpoint(db: Session = Depends(get_db)):
    return recent_projects(db)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project_endpoint(
    project_id: uuid.UUID, payload: UpdateProjectRequest, db: Session = Depends(get_db)
):
    return update_project(db, project_id, payload)

