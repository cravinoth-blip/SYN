import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.db.session import Base
from app.db.types import GUID


JsonType = JSON().with_variant(JSONB, "postgresql")


class SectionName(str, enum.Enum):
    CONDITION = "Condition"
    COMPOUND = "Compound"
    CONTEXT = "Context"
    COMPANY = "Company"
    CUSTOMER = "Customer"
    CHANNEL = "Channel"
    COMPETITION = "Competition"


class SourceType(str, enum.Enum):
    PUBMED = "PubMed"
    PMC = "PMC"
    CLINICAL_TRIALS = "ClinicalTrials"
    REGULATORY = "Regulatory"
    HTA = "HTA"
    CONGRESS = "Congress"
    NEWS = "News"
    GUIDELINE = "Guideline"
    EPIDEMIOLOGY = "Epidemiology"
    ADVOCACY = "Advocacy"
    INTERNAL_UPLOAD = "InternalUpload"


class EvidenceClassification(str, enum.Enum):
    FACT_BACKED = "FactBacked"
    AI_INFERENCE = "AIInference"
    CLIENT_INTERNAL_INPUT = "ClientInternalInput"


class CandidateStatus(str, enum.Enum):
    DRAFT_GENERATED = "DRAFT_GENERATED"
    VALIDATION_IN_PROGRESS = "VALIDATION_IN_PROGRESS"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATED_READY = "VALIDATED_READY"


class PublishStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"


class ScopeType(str, enum.Enum):
    FULL = "full"
    SECTION = "section"


class JobStatus(str, enum.Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


class ExportType(str, enum.Enum):
    PDF = "PDF"
    PPTX = "PPTX"


class Project(Base):
    __tablename__ = "project"

    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    disease: Mapped[str] = mapped_column(String(255), nullable=False)
    subtype_biomarker: Mapped[str | None] = mapped_column(String(255))
    line_of_therapy: Mapped[str | None] = mapped_column(String(255))
    geography: Mapped[str] = mapped_column(String(255), nullable=False)
    optional_brief: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    files: Mapped[list["ProjectFile"]] = relationship(back_populates="project")
    versions: Mapped[list["Version"]] = relationship(back_populates="project")


class ProjectFile(Base):
    __tablename__ = "project_file"

    file_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("project.project_id"))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(64), default="pending")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(GUID())

    project: Mapped[Project] = relationship(back_populates="files")
    parsed_document: Mapped["ParsedDocument | None"] = relationship(back_populates="file")


class ParsedDocument(Base):
    __tablename__ = "parsed_document"

    parsed_document_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("project_file.file_id"))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file: Mapped[ProjectFile] = relationship(back_populates="parsed_document")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="parsed_document")


class DocumentChunk(Base):
    __tablename__ = "document_chunk"

    chunk_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    parsed_document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("parsed_document.parsed_document_id")
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_ref: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    parsed_document: Mapped[ParsedDocument] = relationship(back_populates="chunks")


class CandidateVersion(Base):
    __tablename__ = "candidate_version"

    candidate_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("project.project_id"))
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    scope_type: Mapped[ScopeType] = mapped_column(Enum(ScopeType), default=ScopeType.FULL)
    status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus), default=CandidateStatus.DRAFT_GENERATED
    )
    selected_section: Mapped[str | None] = mapped_column(String(64))
    change_instruction: Mapped[str | None] = mapped_column(Text)
    excluded_source_categories: Mapped[list[str]] = mapped_column(JsonType, default=list)
    excluded_document_ids: Mapped[list[str]] = mapped_column(JsonType, default=list)
    candidate_payload_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())


class ValidationReport(Base):
    __tablename__ = "validation_report"

    validation_report_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    candidate_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("candidate_version.candidate_version_id")
    )
    overall_status: Mapped[str] = mapped_column(String(64), nullable=False)
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    findings: Mapped[list["ValidationFinding"]] = relationship(back_populates="validation_report")


class ValidationFinding(Base):
    __tablename__ = "validation_finding"

    finding_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    validation_report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("validation_report.validation_report_id")
    )
    finding_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    section_name: Mapped[str | None] = mapped_column(String(64))
    claim_excerpt: Mapped[str | None] = mapped_column(Text)
    related_source_ids: Mapped[list[str]] = mapped_column(JsonType, default=list)
    recommended_action: Mapped[str | None] = mapped_column(Text)

    validation_report: Mapped[ValidationReport] = relationship(back_populates="findings")


class EvidenceItem(Base):
    __tablename__ = "evidence_item"

    evidence_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("project.project_id"))
    candidate_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    section_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_date: Mapped[date | None] = mapped_column(Date)
    geography: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    relevance: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0.75)
    evidence_strength: Mapped[str] = mapped_column(String(64), default="Medium")
    classification: Mapped[EvidenceClassification] = mapped_column(
        Enum(EvidenceClassification), default=EvidenceClassification.FACT_BACKED
    )
    universal_fields_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    section_specific_fields_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    notes: Mapped[str | None] = mapped_column(Text)


class Version(Base):
    __tablename__ = "version"

    version_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("project.project_id"))
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    source_candidate_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("candidate_version.candidate_version_id")
    )
    publish_status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus), default=PublishStatus.PUBLISHED
    )
    latest_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_by: Mapped[uuid.UUID | None] = mapped_column(GUID())

    project: Mapped[Project] = relationship(back_populates="versions")
    sections: Mapped[list["SectionOutput"]] = relationship(back_populates="version")


class SectionOutput(Base):
    __tablename__ = "section_output"

    section_output_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("version.version_id"))
    section_name: Mapped[str] = mapped_column(String(64), nullable=False)
    narrative_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    structured_fields_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    validation_status: Mapped[str] = mapped_column(String(64), default="validated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    version: Mapped[Version] = relationship(back_populates="sections")


class Citation(Base):
    __tablename__ = "citation"

    citation_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("version.version_id"))
    global_reference_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_name: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("evidence_item.evidence_id"))
    formatted_reference: Mapped[str] = mapped_column(Text, nullable=False)
    clickable_link: Mapped[str | None] = mapped_column(String(2048))


class ExportJob(Base):
    __tablename__ = "export_job"

    export_job_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("version.version_id"))
    export_type: Mapped[ExportType] = mapped_column(Enum(ExportType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED)
    artifact_uri: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    requested_by: Mapped[uuid.UUID | None] = mapped_column(GUID())


class AuditLog(Base):
    __tablename__ = "audit_log"

    audit_id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("project.project_id"))
    version_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    payload_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

