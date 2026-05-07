import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import (
    CandidateStatus,
    CandidateVersion,
    Citation,
    EvidenceItem,
    PublishStatus,
    SectionOutput,
    Version,
)
from app.services.audit import record_audit
from app.services.common import SECTIONS


def get_candidate(db: Session, candidate_version_id: uuid.UUID) -> CandidateVersion:
    candidate = db.get(CandidateVersion, candidate_version_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate version not found")
    return candidate


def publish_candidate(db: Session, candidate_version_id: uuid.UUID) -> Version:
    candidate = get_candidate(db, candidate_version_id)
    if candidate.status != CandidateStatus.VALIDATED_READY:
        raise HTTPException(status_code=409, detail="Only validated candidates can be published")

    db.execute(
        update(Version)
        .where(Version.project_id == candidate.project_id, Version.latest_flag.is_(True))
        .values(latest_flag=False)
    )

    version = Version(
        project_id=candidate.project_id,
        parent_version_id=candidate.parent_version_id,
        source_candidate_version_id=candidate.candidate_version_id,
        publish_status=PublishStatus.PUBLISHED,
        latest_flag=True,
    )
    db.add(version)
    db.flush()

    payload = candidate.candidate_payload_json or {}
    sections_payload: dict[str, Any] = payload.get("sections", {})

    if candidate.scope_type.value == "section" and candidate.parent_version_id:
        parent_sections = db.scalars(
            select(SectionOutput).where(SectionOutput.version_id == candidate.parent_version_id)
        )
        for parent_section in parent_sections:
            if parent_section.section_name not in sections_payload:
                sections_payload[parent_section.section_name] = {
                    "narrative_markdown": parent_section.narrative_markdown,
                    "structured_fields": parent_section.structured_fields_json,
                }

    for section in SECTIONS:
        section_payload = sections_payload.get(section)
        if not section_payload:
            continue
        db.add(
            SectionOutput(
                version_id=version.version_id,
                section_name=section,
                narrative_markdown=section_payload["narrative_markdown"],
                structured_fields_json=section_payload.get("structured_fields", {}),
                validation_status="validated",
            )
        )

    evidence = list(
        db.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.candidate_version_id == candidate.candidate_version_id)
            .order_by(EvidenceItem.section_name, EvidenceItem.source_title)
        )
    )
    reference_number = 1
    for item in evidence:
        formatted = f"{item.source_title}. {item.source_type.value}. {item.source_date or 'n.d.'}."
        db.add(
            Citation(
                version_id=version.version_id,
                global_reference_number=reference_number,
                section_name=item.section_name,
                evidence_id=item.evidence_id,
                formatted_reference=formatted,
                clickable_link=(item.universal_fields_json or {}).get("url"),
            )
        )
        reference_number += 1

    record_audit(
        db,
        "version.published",
        project_id=candidate.project_id,
        version_id=version.version_id,
        payload={"candidate_version_id": str(candidate.candidate_version_id)},
    )
    db.commit()
    db.refresh(version)
    return version


def list_versions(db: Session, project_id: uuid.UUID) -> list[Version]:
    return list(
        db.scalars(
            select(Version).where(Version.project_id == project_id).order_by(Version.published_at.desc())
        )
    )


def get_published_version(db: Session, version_id: uuid.UUID) -> Version:
    version = db.get(Version, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version

