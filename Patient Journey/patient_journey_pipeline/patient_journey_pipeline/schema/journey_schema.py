"""
Patient Journey Map — Structured Schema

This defines the data contract between all 4 passes.
Pass 1 populates it. Pass 2 annotates it with confidence.
Pass 3 reads it to build artifacts. Pass 4 renders it to prose.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNSUPPORTED = "UNSUPPORTED"


JOURNEY_PHASES = [
    "presentation",
    "diagnosis",
    "treatment",
    "re_diagnosis",
    "tx_adaptation",
    "living_with",
]


# ─── The JSON schema sent to the model for structured output ────

JOURNEY_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "disease": {"type": "string"},
        "summary": {"type": "string", "description": "Executive summary of the patient journey"},
        "phases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "phase_id": {
                        "type": "string",
                        "enum": JOURNEY_PHASES,
                    },
                    "headline": {
                        "type": "string",
                        "description": "One-line headline capturing this phase",
                    },
                    "feelings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Dominant emotions in this phase (e.g. Stress, Hope, Frustration)",
                    },
                    "moment": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "emotional_arc": {
                                "type": "string",
                                "enum": ["rising", "falling", "stable", "volatile"],
                            },
                        },
                        "required": ["title", "description"],
                    },
                    "mindset": {
                        "type": "string",
                        "description": "Patient's internal monologue / beliefs in this phase",
                    },
                    "pain_points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "stakeholder": {
                                    "type": "string",
                                    "description": "Who can address this (PCP, specialist, insurer, pharma, etc.)",
                                },
                                "severity": {
                                    "type": "string",
                                    "enum": ["critical", "high", "moderate", "low"],
                                },
                            },
                            "required": ["description"],
                        },
                    },
                    "evidence_claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim": {"type": "string"},
                                "source": {"type": "string"},
                                "source_type": {
                                    "type": "string",
                                    "enum": [
                                        "spine",
                                        "web",
                                        "clinical_trial",
                                        "fda_label",
                                        "ci_supplement",
                                        "model_inference",
                                    ],
                                },
                                "citation_id": {"type": "string"},
                            },
                            "required": ["claim", "source_type"],
                        },
                    },
                    "unmet_needs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    # ── Added by Pass 2 ──
                    "confidence": {
                        "type": "string",
                        "enum": ["HIGH", "MEDIUM", "LOW", "UNSUPPORTED"],
                        "description": "Set by Pass 2 verification",
                    },
                    "verification_notes": {
                        "type": "string",
                        "description": "Pass 2 reviewer commentary",
                    },
                    "gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Evidence gaps identified by Pass 2",
                    },
                },
                "required": ["phase_id", "headline", "feelings", "moment", "mindset", "pain_points"],
            },
        },
        "assumptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicit assumptions made during generation",
        },
        "declared_artifacts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["excel", "csv", "template"]},
                    "description": {"type": "string"},
                    "tabs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "For Excel: list of worksheet names",
                    },
                },
                "required": ["name", "type", "description"],
            },
            "description": "Artifacts to be built in Pass 3",
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "citation_id": {"type": "string"},
                    "full_reference": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["citation_id", "full_reference"],
            },
        },
    },
    "required": ["disease", "summary", "phases"],
}
