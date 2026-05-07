import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EvidenceClassification, EvidenceItem, Project, SourceType
from app.services.connectors import SourceEnvelope


SOURCE_QUALITY = {
    SourceType.PUBMED.value: 0.92,
    SourceType.PMC.value: 0.9,
    SourceType.CLINICAL_TRIALS.value: 0.9,
    SourceType.GUIDELINE.value: 0.88,
    SourceType.REGULATORY.value: 0.88,
    SourceType.HTA.value: 0.84,
    SourceType.EPIDEMIOLOGY.value: 0.82,
    SourceType.CONGRESS.value: 0.72,
    SourceType.NEWS.value: 0.62,
    SourceType.ADVOCACY.value: 0.58,
    SourceType.INTERNAL_UPLOAD.value: 0.76,
}


def score_evidence(source_type: str, source_date: date | None) -> tuple[float, str]:
    base = SOURCE_QUALITY.get(source_type, 0.65)
    if source_date and source_date.year >= date.today().year - 2:
        base += 0.04
    score = min(base, 0.98)
    strength = "High" if score >= 0.86 else "Medium" if score >= 0.68 else "Low"
    return round(score, 2), strength


def normalize_envelopes(
    db: Session,
    *,
    project: Project,
    candidate_version_id: uuid.UUID,
    envelopes: list[SourceEnvelope],
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for envelope in envelopes:
        confidence, strength = score_evidence(envelope.source_type, envelope.source_date)
        classification = (
            EvidenceClassification.CLIENT_INTERNAL_INPUT
            if envelope.source_type == SourceType.INTERNAL_UPLOAD.value
            else EvidenceClassification.FACT_BACKED
        )
        item = EvidenceItem(
            project_id=project.project_id,
            candidate_version_id=candidate_version_id,
            section_name=envelope.candidate_section,
            source_type=SourceType(envelope.source_type),
            source_title=envelope.source_title[:1024],
            source_date=envelope.source_date,
            geography=envelope.geography,
            summary=envelope.extracted_summary or envelope.source_title,
            relevance=f"Supports {envelope.candidate_section} analysis for {project.disease}.",
            confidence_score=confidence,
            evidence_strength=strength,
            classification=classification,
            universal_fields_json={
                "url": envelope.url,
                "source_type": envelope.source_type,
                "provenance": envelope.provenance,
            },
            section_specific_fields_json={
                "section": envelope.candidate_section,
                "raw_payload_preview": envelope.raw_payload,
            },
            notes=None,
        )
        db.add(item)
        items.append(item)
    db.flush()
    return items


def evidence_for_candidate(db: Session, candidate_version_id: uuid.UUID) -> list[EvidenceItem]:
    return list(
        db.scalars(select(EvidenceItem).where(EvidenceItem.candidate_version_id == candidate_version_id))
    )


def evidence_for_project_section(
    db: Session, project_id: uuid.UUID, section_name: str, limit: int = 12
) -> list[EvidenceItem]:
    statement = (
        select(EvidenceItem)
        .where(EvidenceItem.project_id == project_id, EvidenceItem.section_name == section_name)
        .limit(limit)
    )
    return list(db.scalars(statement))


def seed_development_evidence(
    db: Session, *, project: Project, candidate_version_id: uuid.UUID, section_name: str
) -> EvidenceItem:
    confidence, strength = score_evidence(SourceType.PUBMED.value, None)
    item = EvidenceItem(
        project_id=project.project_id,
        candidate_version_id=candidate_version_id,
        section_name=section_name,
        source_type=SourceType.PUBMED,
        source_title=f"Development evidence placeholder for {project.disease} {section_name}",
        source_date=None,
        geography=project.geography,
        summary=(
            f"Development fallback evidence for {section_name}. Live connectors replace this "
            "when API/network access is available."
        ),
        relevance=f"Ensures {section_name} can be validated in local development.",
        confidence_score=confidence,
        evidence_strength=strength,
        classification=EvidenceClassification.FACT_BACKED,
        universal_fields_json={"development_fallback": True},
        section_specific_fields_json={"section": section_name},
        notes="Remove fallback evidence for controlled production runs if strict live-only evidence is required.",
    )
    db.add(item)
    db.flush()
    return item
