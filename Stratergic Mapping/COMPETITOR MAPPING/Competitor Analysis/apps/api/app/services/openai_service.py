import json
from typing import Any

from app.core.config import get_settings


settings = get_settings()

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "threats": {"type": "array", "items": {"type": "string"}},
        "opportunities": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "narrative": {"type": "string"},
    },
    "required": ["summary", "threats", "opportunities", "recommendations", "narrative"],
    "additionalProperties": False,
}


def openai_enabled() -> bool:
    return bool(settings.openai_api_key)


def generate_structured_analysis(
    *,
    pass_name: str,
    task: str,
    workspace_json: dict[str, Any],
    requirements: dict[str, Any],
    prior_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not openai_enabled():
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = {
        "task": task,
        "pass": pass_name,
        "requirements": requirements,
        "workspace": workspace_json,
        "prior_outputs": prior_outputs or {},
        "instructions": [
            "Generate competitor analysis content for a pharma/biotech strategy workspace.",
            "Use only the workspace data and validated evidence provided in the JSON.",
            "Separate strategic inference from source-backed facts in wording.",
            "Return concise but presentation-ready content.",
        ],
    }

    response = client.responses.create(
        model=settings.openai_model,
        instructions=(
            "You are a pharmaceutical competitor intelligence analyst. "
            "Return only JSON that matches the requested schema."
        ),
        input=json.dumps(prompt),
        text={
            "format": {
                "type": "json_schema",
                "name": "competitor_analysis",
                "strict": True,
                "schema": ANALYSIS_SCHEMA,
            }
        },
    )
    return json.loads(response.output_text)
