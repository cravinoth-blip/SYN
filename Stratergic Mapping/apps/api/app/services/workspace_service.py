import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Citation, EvidenceItem, Project, ProjectFile, SectionOutput, Version
from app.schemas import (
    CitationResponse,
    EvidenceResponse,
    ProjectResponse,
    SectionWorkspaceResponse,
    VersionSummaryResponse,
    WorkspaceResponse,
)
from app.services.project_service import latest_version_for_project
from app.services.version_service import list_versions


def build_workspace(db: Session, project_id: uuid.UUID, version_id: uuid.UUID | None = None) -> WorkspaceResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    version = db.get(Version, version_id) if version_id else latest_version_for_project(db, project_id)
    if not version:
        raise HTTPException(status_code=404, detail="No published version exists for this project")

    sections = list(
        db.scalars(
            select(SectionOutput)
            .where(SectionOutput.version_id == version.version_id)
            .order_by(SectionOutput.section_name)
        )
    )
    citations = list(
        db.scalars(
            select(Citation)
            .where(Citation.version_id == version.version_id)
            .order_by(Citation.global_reference_number)
        )
    )
    citations_by_section = {}
    for citation in citations:
        citations_by_section.setdefault(citation.section_name, []).append(citation)

    section_responses: list[SectionWorkspaceResponse] = []
    for section in sections:
        evidence_ids = [c.evidence_id for c in citations_by_section.get(section.section_name, [])]
        evidence = (
            list(db.scalars(select(EvidenceItem).where(EvidenceItem.evidence_id.in_(evidence_ids))))
            if evidence_ids
            else []
        )
        section_responses.append(
            SectionWorkspaceResponse(
                section_name=section.section_name,
                narrative_markdown=section.narrative_markdown,
                structured_fields=section.structured_fields_json,
                evidence=[
                    EvidenceResponse(
                        evidence_id=item.evidence_id,
                        source_type=item.source_type.value,
                        source_title=item.source_title,
                        source_date=str(item.source_date) if item.source_date else None,
                        geography=item.geography,
                        summary=item.summary,
                        relevance=item.relevance,
                        confidence_score=float(item.confidence_score),
                        evidence_strength=item.evidence_strength,
                        classification=item.classification.value,
                        notes=item.notes,
                    )
                    for item in evidence
                ],
                citations=[CitationResponse.model_validate(c, from_attributes=True) for c in citations_by_section.get(section.section_name, [])],
            )
        )

    uploads = list(db.scalars(select(ProjectFile).where(ProjectFile.project_id == project_id)))
    history = list_versions(db, project_id)
    return WorkspaceResponse(
        project=ProjectResponse.model_validate(project),
        latest_version=VersionSummaryResponse.model_validate(version, from_attributes=True),
        history=[VersionSummaryResponse.model_validate(item, from_attributes=True) for item in history],
        sections=section_responses,
        global_citation_map=[CitationResponse.model_validate(c, from_attributes=True) for c in citations],
        available_regeneration_exclusions={
            "source_categories": [
                "PubMed",
                "ClinicalTrials",
                "Guideline",
                "Regulatory",
                "HTA",
                "Epidemiology",
                "Congress",
                "News",
                "Advocacy",
                "InternalUpload",
            ],
            "uploaded_files": [
                {"file_id": str(file.file_id), "filename": file.filename, "parse_status": file.parse_status}
                for file in uploads
            ],
        },
        export_availability={"pdf": True, "pptx": True},
    )

