from __future__ import annotations

from openai import OpenAI

from app.core.config import get_settings
from app.models import EvidenceItem, Project
from app.services.common import SECTION_GUIDANCE


settings = get_settings()


def _fallback_section(project: Project, section_name: str, evidence: list[EvidenceItem]) -> str:
    snippets = " ".join(item.summary for item in evidence[:3])
    citation_numbers = ", ".join(f"[{idx}]" for idx in range(1, min(len(evidence), 3) + 1)) or "[1]"
    return (
        f"## {section_name}\n\n"
        f"{section_name} analysis for {project.disease} in {project.geography} should focus on "
        f"{SECTION_GUIDANCE[section_name]}. The current evidence bundle indicates that the "
        f"selected scope ({project.subtype_biomarker or 'general population'}, "
        f"{project.line_of_therapy or 'all relevant lines'}) requires an integrated view of "
        f"clinical, market, and stakeholder implications {citation_numbers}.\n\n"
        f"Key evidence signal: {snippets[:900]}\n\n"
        "**Recommendation:** Preserve traceable source-backed claims, separate AI inference from "
        "client/internal input, and flag low-confidence areas for reviewer attention."
    )


def generate_section_narrative(
    project: Project,
    section_name: str,
    evidence: list[EvidenceItem],
    *,
    change_instruction: str | None = None,
    prior_context: str | None = None,
) -> str:
    if not settings.openai_api_key:
        return _fallback_section(project, section_name, evidence)

    client = OpenAI(api_key=settings.openai_api_key)
    evidence_lines = "\n".join(
        f"- {item.source_title}: {item.summary} ({item.source_type.value}, confidence {item.confidence_score})"
        for item in evidence[:12]
    )
    prompt = f"""
You are generating one section of a traceable 7Cs disease intelligence report.

Project:
- Disease: {project.disease}
- Biomarker/subtype: {project.subtype_biomarker or "not specified"}
- Line of therapy: {project.line_of_therapy or "not specified"}
- Geography: {project.geography}
- Client/account: {project.client_name}
- Optional brief: {project.optional_brief or "none"}

Section: {section_name}
Section focus: {SECTION_GUIDANCE[section_name]}
Change instruction: {change_instruction or "initial generation"}
Prior context: {prior_context or "none"}

Evidence bundle:
{evidence_lines}

Return detailed markdown narrative. Use bracketed citation placeholders such as [1], [2].
Label recommendations and caveats clearly. Do not cite evidence outside this evidence bundle.
"""
    response = client.responses.create(
        model=settings.openai_model,
        input=prompt,
        temperature=0.2,
    )
    return response.output_text

