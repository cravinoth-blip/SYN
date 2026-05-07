from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class SourceEnvelope:
    source_title: str
    source_type: str
    source_date: date | None
    url: str | None
    geography: str | None
    raw_payload: dict[str, Any]
    extracted_summary: str
    candidate_section: str
    provenance: dict[str, Any] = field(default_factory=dict)


class SourceConnector:
    source_type: str

    async def retrieve(self, plan: dict[str, Any]) -> list[SourceEnvelope]:
        raise NotImplementedError

