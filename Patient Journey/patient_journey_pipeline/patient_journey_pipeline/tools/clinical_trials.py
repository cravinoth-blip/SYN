"""
Tool 4: ClinicalTrials.gov — real-time trial registry data.

Uses the v2 API (no key required). Returns trial design, endpoints,
enrollment, status, sponsor, and phase information.
"""

import config
from tools.base import BaseTool, corporate_session


class ClinicalTrialsTool(BaseTool):
    def __init__(self):
        self._session = corporate_session()
    name = "search_clinical_trials"
    description = (
        "Search ClinicalTrials.gov for clinical trials related to a disease or "
        "intervention. Returns trial design, endpoints, enrollment status, phase, "
        "sponsor, and key dates. Use for treatment landscape and pipeline analysis."
    )

    def _execute(
        self,
        condition: str = "",
        intervention: str = "",
        status: str = "",
        phase: str = "",
        max_results: int = 10,
    ) -> dict:
        params = {
            "format": "json",
            "pageSize": min(max_results, 50),
        }

        # Build query filter
        query_parts = []
        if condition:
            query_parts.append(f"AREA[Condition]{condition}")
        if intervention:
            query_parts.append(f"AREA[Intervention]{intervention}")
        if status:
            params["filter.overallStatus"] = status
        if phase:
            query_parts.append(f"AREA[Phase]{phase}")

        if query_parts:
            params["query.term"] = " AND ".join(query_parts)
        elif condition:
            params["query.cond"] = condition

        resp = self._session.get(config.CLINICAL_TRIALS_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        trials = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            outcomes_module = protocol.get("outcomesModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

            primary_outcomes = []
            for o in outcomes_module.get("primaryOutcomes", []):
                primary_outcomes.append({
                    "measure": o.get("measure", ""),
                    "timeFrame": o.get("timeFrame", ""),
                })

            trials.append({
                "nct_id": id_module.get("nctId", ""),
                "title": id_module.get("briefTitle", ""),
                "status": status_module.get("overallStatus", ""),
                "phase": ", ".join(design_module.get("phases", [])),
                "enrollment": status_module.get("enrollmentInfo", {}).get("count", ""),
                "sponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
                "start_date": status_module.get("startDateStruct", {}).get("date", ""),
                "primary_outcomes": primary_outcomes,
                "study_type": design_module.get("studyType", ""),
            })

        return {
            "result": trials,
            "summary": f"{len(trials)} trials found for '{condition or intervention}'",
            "sources": [
                {
                    "title": t["title"],
                    "url": f"https://clinicaltrials.gov/study/{t['nct_id']}",
                }
                for t in trials
            ],
        }

    def openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "condition": {
                            "type": "string",
                            "description": "Disease or condition name (e.g. 'Systemic Lupus Erythematosus')",
                        },
                        "intervention": {
                            "type": "string",
                            "description": "Drug or intervention name (e.g. 'belimumab')",
                        },
                        "status": {
                            "type": "string",
                            "description": "Trial status filter: RECRUITING, COMPLETED, ACTIVE_NOT_RECRUITING, etc.",
                        },
                        "phase": {
                            "type": "string",
                            "description": "Trial phase: Phase 1, Phase 2, Phase 3, Phase 4",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of trials to return (default 10)",
                        },
                    },
                    "required": [],
                },
            },
        }
