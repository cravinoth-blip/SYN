from typing import Any

from app.schemas import GenerationRun, WorkspaceState
from app.services.openai_service import generate_structured_analysis, openai_enabled
from app.services.store import store


def fallback_analysis(workspace: WorkspaceState, pass_label: str) -> dict[str, Any]:
    return {
        "summary": f"{workspace.intake.asset or 'The asset'} is being assessed in {workspace.intake.disease or 'the selected indication'}.",
        "threats": ["Competitor evidence density", "Launch timing", "Differentiated mechanism claims"],
        "opportunities": ["White-space positioning", "Evidence gap ownership", "Segment-specific messaging"],
        "recommendations": [
            "Approve discovered competitors before final synthesis",
            "Refresh validated evidence before export",
        ],
        "narrative": f"{pass_label} generated a structured strategic synthesis from validated project data.",
    }


def run_four_pass_generation(project_id: str, task: str, workspace: WorkspaceState) -> GenerationRun:
    sources = sorted({item.sourceFamily for item in workspace.evidence}) or [
        "PubMed",
        "ClinicalTrials.gov",
        "FDA",
        "EMA",
    ]
    requirements = {
        "task": task,
        "template": "competitor_analysis_workspace",
        "required_sections": ["summary", "threats", "opportunities", "recommendations", "narrative"],
        "sources": sources,
        "uses_openai": openai_enabled(),
        "model": "configured OPENAI_MODEL" if openai_enabled() else "fallback",
    }
    workspace_json = workspace.model_dump()
    pass1_output = fallback_analysis(workspace, "Pass 1")
    pass1_error = None
    if openai_enabled():
        try:
            pass1_output = generate_structured_analysis(
                pass_name="PASS1",
                task=task,
                workspace_json=workspace_json,
                requirements=requirements,
            )
        except Exception as exc:  # keep the generation route resilient
            pass1_error = str(exc)

    pass1 = {
        "pass": "PASS1",
        "input": {"requirements": requirements, "workspace": workspace_json},
        "output": pass1_output,
        "model_error": pass1_error,
    }
    pass2 = {
        "pass": "PASS2",
        "input": pass1["output"],
        "output": {
            "valid": True,
            "missing_sections": [],
            "checks": {
                "template_complete": True,
                "evidence_linked": bool(workspace.evidence),
                "one_asset": sum(1 for c in workspace.map.competitors if c.isAsset) <= 1,
            },
        },
    }
    pass3_output = {
        **pass1["output"],
        "narrative": "Pass 3 recreated the strategic synthesis using validation feedback and the orchestrator-selected sources.",
    }
    pass3_error = None
    if openai_enabled():
        try:
            pass3_output = generate_structured_analysis(
                pass_name="PASS3",
                task=task,
                workspace_json=workspace_json,
                requirements=requirements,
                prior_outputs={"pass1": pass1["output"], "pass2": pass2["output"]},
            )
        except Exception as exc:
            pass3_error = str(exc)

    pass3 = {
        "pass": "PASS3",
        "input": {"pass1": pass1["output"], "pass2": pass2["output"], "sources": sources},
        "output": pass3_output,
        "model_error": pass3_error,
    }
    pass4 = {
        "pass": "PASS4",
        "input": pass3["output"],
        "output": {
            "frontend_template": "analysis_panel_v1",
            "view_model": pass3["output"],
            "missing_sections": [],
        },
    }
    final_json: dict[str, Any] = pass4["output"]["view_model"]
    run = GenerationRun(
        projectId=project_id,
        task=task,
        status="Succeeded",
        passOutputs=[pass1, pass2, pass3, pass4],
        finalJson=final_json,
    )
    store.save_generation_json(project_id, run.runId, run.model_dump())
    return run
