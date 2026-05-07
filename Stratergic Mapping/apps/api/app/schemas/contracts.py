import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import CandidateStatus, ExportType, JobStatus, ScopeType


class CreateProjectRequest(BaseModel):
    project_name: str
    disease: str
    geography: str
    client_name: str
    subtype_biomarker: str | None = None
    line_of_therapy: str | None = None
    optional_brief: str | None = None


class UpdateProjectRequest(BaseModel):
    project_name: str | None = None
    disease: str | None = None
    geography: str | None = None
    client_name: str | None = None
    subtype_biomarker: str | None = None
    line_of_therapy: str | None = None
    optional_brief: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    project_name: str
    disease: str
    geography: str
    client_name: str
    subtype_biomarker: str | None = None
    line_of_therapy: str | None = None
    optional_brief: str | None = None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    file_type: str
    storage_uri: str
    parse_status: str
    uploaded_at: datetime


class GenerateProjectRequest(BaseModel):
    force_refresh: bool = False


class RegenerateFullRequest(BaseModel):
    parent_version_id: uuid.UUID
    change_instruction: str = Field(min_length=1)
    excluded_source_categories: list[str] = Field(default_factory=list)
    excluded_document_ids: list[str] = Field(default_factory=list)


class RegenerateSectionRequest(RegenerateFullRequest):
    section_name: str


class JobResponse(BaseModel):
    job_id: uuid.UUID
    status: JobStatus
    message: str
    candidate_version_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    export_job_id: uuid.UUID | None = None


class CandidateVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_version_id: uuid.UUID
    project_id: uuid.UUID
    parent_version_id: uuid.UUID | None
    scope_type: ScopeType
    status: CandidateStatus
    selected_section: str | None
    change_instruction: str | None
    excluded_source_categories: list[str]
    excluded_document_ids: list[str]
    created_at: datetime


class ValidationFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: uuid.UUID
    finding_type: str
    severity: str
    section_name: str | None
    claim_excerpt: str | None
    related_source_ids: list[str]
    recommended_action: str | None


class ValidationReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    validation_report_id: uuid.UUID
    candidate_version_id: uuid.UUID
    overall_status: str
    overall_score: float
    created_at: datetime
    findings: list[ValidationFindingResponse] = Field(default_factory=list)


class EvidenceResponse(BaseModel):
    evidence_id: uuid.UUID
    source_type: str
    source_title: str
    source_date: str | None = None
    geography: str | None = None
    summary: str
    relevance: str
    confidence_score: float
    evidence_strength: str
    classification: str
    notes: str | None = None


class CitationResponse(BaseModel):
    citation_id: uuid.UUID
    global_reference_number: int
    section_name: str
    evidence_id: uuid.UUID
    formatted_reference: str
    clickable_link: str | None = None


class SectionWorkspaceResponse(BaseModel):
    section_name: str
    narrative_markdown: str
    structured_fields: dict[str, Any]
    evidence: list[EvidenceResponse]
    citations: list[CitationResponse]


class VersionSummaryResponse(BaseModel):
    version_id: uuid.UUID
    parent_version_id: uuid.UUID | None
    source_candidate_version_id: uuid.UUID
    latest_flag: bool
    publish_status: str
    published_at: datetime


class WorkspaceResponse(BaseModel):
    project: ProjectResponse
    latest_version: VersionSummaryResponse
    history: list[VersionSummaryResponse]
    sections: list[SectionWorkspaceResponse]
    global_citation_map: list[CitationResponse]
    available_regeneration_exclusions: dict[str, Any]
    export_availability: dict[str, bool]


class ExportResponse(BaseModel):
    export_job_id: uuid.UUID
    version_id: uuid.UUID
    export_type: ExportType
    status: JobStatus
    artifact_uri: str | None = None
    created_at: datetime

