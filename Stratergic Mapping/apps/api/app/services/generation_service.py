import uuid

from sqlalchemy.orm import Session

from app.models import CandidateVersion, Project, ScopeType
from app.services.audit import record_audit
from app.services.common import SECTIONS
from app.services.connectors import build_connectors
from app.services.evidence_service import normalize_envelopes, seed_development_evidence
from app.services.llm_router import generate_section_narrative
from app.services.project_service import validate_project_scope
from app.services.retrieval_planner import build_retrieval_plan


async def create_initial_candidate(db: Session, project: Project) -> CandidateVersion:
    validate_project_scope(project)
    candidate = CandidateVersion(project_id=project.project_id, scope_type=ScopeType.FULL)
    db.add(candidate)
    db.flush()
    await _generate_candidate_payload(db, project=project, candidate=candidate)
    record_audit(
        db,
        "generation.candidate_created",
        project_id=project.project_id,
        payload={"candidate_version_id": str(candidate.candidate_version_id)},
    )
    return candidate


async def create_regeneration_candidate(
    db: Session,
    project: Project,
    *,
    parent_version_id: uuid.UUID,
    scope_type: ScopeType,
    selected_section: str | None,
    change_instruction: str,
    excluded_source_categories: list[str],
    excluded_document_ids: list[str],
) -> CandidateVersion:
    validate_project_scope(project)
    candidate = CandidateVersion(
        project_id=project.project_id,
        parent_version_id=parent_version_id,
        scope_type=scope_type,
        selected_section=selected_section,
        change_instruction=change_instruction,
        excluded_source_categories=excluded_source_categories,
        excluded_document_ids=excluded_document_ids,
    )
    db.add(candidate)
    db.flush()
    await _generate_candidate_payload(db, project=project, candidate=candidate)
    record_audit(
        db,
        "regeneration.candidate_created",
        project_id=project.project_id,
        payload={
            "candidate_version_id": str(candidate.candidate_version_id),
            "scope_type": candidate.scope_type.value,
            "selected_section": candidate.selected_section,
        },
    )
    return candidate


async def _generate_candidate_payload(
    db: Session, *, project: Project, candidate: CandidateVersion
) -> None:
    plan = build_retrieval_plan(
        project,
        scope_type=candidate.scope_type.value,
        selected_section=candidate.selected_section,
        parent_version_id=str(candidate.parent_version_id) if candidate.parent_version_id else None,
        change_instruction=candidate.change_instruction,
        excluded_source_categories=candidate.excluded_source_categories,
        excluded_document_ids=candidate.excluded_document_ids,
    )
    connectors = build_connectors(db)
    sections_payload: dict[str, dict] = {}

    for section_plan in plan:
        section_name = section_plan["section_name"]
        envelopes = []
        connector_failures = []
        excluded = set(candidate.excluded_source_categories or [])
        for connector in connectors:
            if connector.source_type in excluded:
                continue
            try:
                envelopes.extend(await connector.retrieve(section_plan))
            except Exception as exc:
                connector_failures.append({"connector": connector.source_type, "error": str(exc)})

        evidence = normalize_envelopes(
            db,
            project=project,
            candidate_version_id=candidate.candidate_version_id,
            envelopes=envelopes,
        )
        if not evidence:
            evidence = [
                seed_development_evidence(
                    db,
                    project=project,
                    candidate_version_id=candidate.candidate_version_id,
                    section_name=section_name,
                )
            ]

        narrative = generate_section_narrative(
            project,
            section_name,
            evidence,
            change_instruction=candidate.change_instruction,
        )
        sections_payload[section_name] = {
            "narrative_markdown": narrative,
            "structured_fields": {
                "connector_failures": connector_failures,
                "evidence_count": len(evidence),
                "source_mix": sorted({item.source_type.value for item in evidence}),
            },
        }

    candidate.candidate_payload_json = {
        "sections": sections_payload,
        "required_sections": SECTIONS,
        "scope_type": candidate.scope_type.value,
        "selected_section": candidate.selected_section,
    }
    db.flush()

