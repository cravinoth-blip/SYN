from typing import Any

from app.models import Project
from app.services.common import SECTION_GUIDANCE, SECTIONS


def build_retrieval_plan(
    project: Project,
    *,
    scope_type: str = "full",
    selected_section: str | None = None,
    parent_version_id: str | None = None,
    change_instruction: str | None = None,
    excluded_source_categories: list[str] | None = None,
    excluded_document_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    sections = [selected_section] if scope_type == "section" and selected_section else SECTIONS
    return [
        {
            "project_id": project.project_id,
            "project_name": project.project_name,
            "disease": project.disease,
            "subtype_biomarker": project.subtype_biomarker,
            "line_of_therapy": project.line_of_therapy,
            "geography": project.geography,
            "client_name": project.client_name,
            "optional_brief": project.optional_brief,
            "section_name": section,
            "section_guidance": SECTION_GUIDANCE[section],
            "parent_version_id": parent_version_id,
            "change_instruction": change_instruction,
            "excluded_source_categories": excluded_source_categories or [],
            "excluded_document_ids": excluded_document_ids or [],
        }
        for section in sections
    ]

