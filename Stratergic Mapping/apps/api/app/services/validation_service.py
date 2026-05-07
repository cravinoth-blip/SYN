import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateStatus, CandidateVersion, ValidationFinding, ValidationReport
from app.services.common import SECTIONS
from app.services.evidence_service import evidence_for_candidate


def validate_candidate(db: Session, candidate: CandidateVersion) -> ValidationReport:
    candidate.status = CandidateStatus.VALIDATION_IN_PROGRESS
    db.flush()

    payload = candidate.candidate_payload_json or {}
    section_names = (
        [candidate.selected_section]
        if candidate.scope_type.value == "section" and candidate.selected_section
        else SECTIONS
    )
    evidence = evidence_for_candidate(db, candidate.candidate_version_id)
    evidence_by_section = {
        section: [item for item in evidence if item.section_name == section] for section in section_names
    }

    findings: list[ValidationFinding] = []
    for section in section_names:
        section_payload = payload.get("sections", {}).get(section)
        if not section_payload or not section_payload.get("narrative_markdown"):
            findings.append(
                ValidationFinding(
                    finding_type="framework_completeness",
                    severity="high",
                    section_name=section,
                    claim_excerpt=None,
                    related_source_ids=[],
                    recommended_action="Generate a narrative for the required 7C section.",
                )
            )
        if not evidence_by_section.get(section):
            findings.append(
                ValidationFinding(
                    finding_type="claim_grounding",
                    severity="medium",
                    section_name=section,
                    claim_excerpt=None,
                    related_source_ids=[],
                    recommended_action="Add at least one normalized evidence item for this section.",
                )
            )

    score = max(0.0, 1.0 - (0.16 * len([f for f in findings if f.severity == "high"])) - (0.08 * len(findings)))
    status = "pass" if score >= 0.78 else "fail"
    report = ValidationReport(
        candidate_version_id=candidate.candidate_version_id,
        overall_status=status,
        overall_score=round(score, 2),
    )
    db.add(report)
    db.flush()
    for finding in findings:
        finding.validation_report_id = report.validation_report_id
        db.add(finding)

    candidate.status = (
        CandidateStatus.VALIDATED_READY
        if status == "pass"
        else CandidateStatus.VALIDATION_FAILED
    )
    db.flush()
    return report


def get_validation_report(db: Session, candidate_version_id: uuid.UUID) -> ValidationReport | None:
    statement = (
        select(ValidationReport)
        .where(ValidationReport.candidate_version_id == candidate_version_id)
        .order_by(ValidationReport.created_at.desc())
        .limit(1)
    )
    return db.scalars(statement).first()

