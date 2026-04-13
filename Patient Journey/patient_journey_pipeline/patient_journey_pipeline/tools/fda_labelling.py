"""
Tool 5: FDA Drug Labelling — current US prescribing information.

Uses the openFDA API (no key required for basic usage).
Returns indications, dosage, warnings, adverse reactions, and more.
"""

import config
from tools.base import BaseTool, corporate_session


class FDALabellingTool(BaseTool):
    def __init__(self):
        self._session = corporate_session()
    name = "search_fda_labels"
    description = (
        "Search FDA drug labelling (prescribing information) for a specific drug. "
        "Returns indications, dosage and administration, warnings, adverse reactions, "
        "contraindications, and clinical pharmacology. Use for understanding approved "
        "treatments, comparing drugs, and identifying safety signals."
    )

    def _execute(
        self,
        drug_name: str,
        sections: list[str] = None,
        max_results: int = 3,
    ) -> dict:
        # Search by brand or generic name
        search_query = f'(openfda.brand_name:"{drug_name}"+openfda.generic_name:"{drug_name}")'
        params = {
            "search": search_query,
            "limit": min(max_results, 10),
        }

        resp = self._session.get(config.FDA_LABEL_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        labels = []
        desired_sections = sections or [
            "indications_and_usage",
            "dosage_and_administration",
            "warnings_and_cautions",
            "adverse_reactions",
            "contraindications",
            "clinical_pharmacology",
            "drug_interactions",
        ]

        for result in data.get("results", []):
            openfda = result.get("openfda", {})
            label = {
                "brand_name": openfda.get("brand_name", [""])[0] if openfda.get("brand_name") else "",
                "generic_name": openfda.get("generic_name", [""])[0] if openfda.get("generic_name") else "",
                "manufacturer": openfda.get("manufacturer_name", [""])[0] if openfda.get("manufacturer_name") else "",
                "route": openfda.get("route", [""])[0] if openfda.get("route") else "",
                "sections": {},
            }

            for section in desired_sections:
                content = result.get(section, [])
                if content:
                    # FDA returns arrays of strings; join and truncate
                    text = " ".join(content)
                    label["sections"][section] = text[:2000]  # Cap per section

            labels.append(label)

        return {
            "result": labels,
            "summary": f"{len(labels)} label(s) found for '{drug_name}'",
            "sources": [
                {
                    "title": f"FDA Label: {l['brand_name'] or l['generic_name']}",
                    "url": f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?query={drug_name}",
                }
                for l in labels
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
                        "drug_name": {
                            "type": "string",
                            "description": "Brand or generic drug name (e.g. 'Humira' or 'adalimumab')",
                        },
                        "sections": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific label sections to retrieve (default: all key sections)",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Number of label results (default 3)",
                        },
                    },
                    "required": ["drug_name"],
                },
            },
        }
