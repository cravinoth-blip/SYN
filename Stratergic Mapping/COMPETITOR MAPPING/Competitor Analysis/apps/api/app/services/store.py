import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas import Intake, ProjectRecord, WorkspaceState, new_id


settings = get_settings()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class WorkspaceStore:
    def __init__(self) -> None:
        self.root = settings.local_data_dir
        self.projects_file = self.root / "projects.json"

    def _workspace_path(self, project_id: str) -> Path:
        return self.root / f"{project_id}.workspace.json"

    def list_projects(self) -> list[ProjectRecord]:
        if not self.projects_file.exists():
            return []
        raw = json.loads(self.projects_file.read_text(encoding="utf-8"))
        return [ProjectRecord.model_validate(item) for item in raw]

    def save_project_index(self, projects: list[ProjectRecord]) -> None:
        self.projects_file.write_text(
            json.dumps([p.model_dump() for p in projects], indent=2), encoding="utf-8"
        )

    def create_project(self, intake: Intake) -> WorkspaceState:
        project_id = new_id("proj")
        workspace = WorkspaceState(projectId=project_id, intake=intake)
        projects = self.list_projects()
        projects.insert(
            0,
            ProjectRecord(
                projectId=project_id,
                projectName=intake.projectName or "Untitled competitor analysis",
                disease=intake.disease,
                asset=intake.asset,
                geography=intake.geography,
                updatedAt=now_iso(),
            ),
        )
        self.save_project_index(projects)
        self.save_workspace(workspace)
        return workspace

    def get_workspace(self, project_id: str) -> WorkspaceState:
        path = self._workspace_path(project_id)
        if not path.exists():
            raise KeyError(project_id)
        return WorkspaceState.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def save_workspace(self, workspace: WorkspaceState) -> WorkspaceState:
        self._workspace_path(workspace.projectId).write_text(
            json.dumps(workspace.model_dump(), indent=2), encoding="utf-8"
        )
        projects = self.list_projects()
        for project in projects:
            if project.projectId == workspace.projectId:
                project.projectName = workspace.intake.projectName or project.projectName
                project.disease = workspace.intake.disease
                project.asset = workspace.intake.asset
                project.geography = workspace.intake.geography
                project.updatedAt = now_iso()
                break
        self.save_project_index(projects)
        return workspace

    def save_generation_json(self, project_id: str, run_id: str, payload: dict[str, Any]) -> Path:
        run_dir = settings.generation_output_dir / project_id / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "run.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path


store = WorkspaceStore()
