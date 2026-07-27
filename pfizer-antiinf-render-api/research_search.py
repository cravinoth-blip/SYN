"""Dynamic PubMed and ClinicalTrials.gov discovery with Snowflake hydration."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any, Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from knowledge_search import SearchSettings, _load_private_key


ResearchSource = Literal["pubmed", "clinical_trials"]
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
TRIALS_SEARCH_URL = "https://clinicaltrials.gov/api/v2/studies"


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"User-Agent": "Syneos-Pfizer-Knowledge-Hub/1.0"},
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _discover_pubmed_ids(query: str, limit: int) -> list[int]:
    payload = _get_json(
        PUBMED_SEARCH_URL,
        {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": limit,
            "sort": "relevance",
            "tool": "syneos_pfizer_knowledge_hub",
        },
    )
    raw_ids = payload.get("esearchresult", {}).get("idlist", [])
    return [int(value) for value in raw_ids if str(value).isdigit()][:limit]


def _discover_trial_ids(query: str, limit: int) -> list[str]:
    payload = _get_json(
        TRIALS_SEARCH_URL,
        {
            "query.term": query,
            "format": "json",
            "pageSize": limit,
            "fields": "NCTId",
        },
    )
    identifiers: list[str] = []
    for study in payload.get("studies", []):
        nct_id = (
            study.get("protocolSection", {})
            .get("identificationModule", {})
            .get("nctId")
        )
        if isinstance(nct_id, str) and nct_id.startswith("NCT"):
            identifiers.append(nct_id)
    return identifiers[:limit]


def _rows(cursor: Any) -> list[dict[str, Any]]:
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


class ResearchSearchClient:
    """Discover arbitrary topics and hydrate results from COMPILE_ADD_ON."""

    def __init__(self, settings: SearchSettings):
        self.settings = settings

    def _connect(self) -> Any:
        import snowflake.connector

        args: dict[str, Any] = {
            "account": self.settings.account,
            "user": self.settings.user,
            "private_key": _load_private_key(self.settings),
            "warehouse": self.settings.warehouse,
            "database": self.settings.database,
            "schema": self.settings.schema,
            "application": "PFIZER_RESEARCH_SEARCH_API",
            "session_parameters": {"STATEMENT_TIMEOUT_IN_SECONDS": 20},
        }
        if self.settings.role:
            args["role"] = self.settings.role
        return snowflake.connector.connect(**args)

    def search(
        self,
        *,
        source: ResearchSource,
        query: str,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        started = time.perf_counter()
        if source == "pubmed":
            identifiers: list[int] | list[str] = _discover_pubmed_ids(query, limit)
        else:
            identifiers = _discover_trial_ids(query, limit)
        if not identifiers:
            return [], int((time.perf_counter() - started) * 1000)

        connection = self._connect()
        try:
            if source == "pubmed":
                results = self._pubmed(connection, identifiers)
            else:
                results = self._clinical_trials(connection, identifiers)
        finally:
            connection.close()
        return results, int((time.perf_counter() - started) * 1000)

    @staticmethod
    def _pubmed(connection: Any, identifiers: list[int] | list[str]) -> list[dict[str, Any]]:
        placeholders = ", ".join(["%s"] * len(identifiers))
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT
                    PUBMED_ID,
                    ARTICLE_TITLE,
                    ABSTRACT,
                    JOURNAL_TITLE,
                    COALESCE(ARTICLE_YEAR, PUBMED_PUB_YEAR, JOURNAL_YEAR)
                        AS PUBLICATION_YEAR,
                    MESH_TERMS,
                    AUTHOR_FORENAME AS FIRST_AUTHOR_FORENAME,
                    AUTHOR_LASTNAME AS FIRST_AUTHOR_LASTNAME,
                    FIRST_AUTHOR_AFFILIATION,
                    ARTICLE_IDENTIFIERS,
                    LANGUAGE
                FROM COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS
                WHERE PUBMED_ID IN ({placeholders})
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY PUBMED_ID
                    ORDER BY AUTHOR_INDEX NULLS LAST
                ) = 1
                """,
                tuple(identifiers),
            )
            found = _rows(cursor)
        finally:
            cursor.close()
        order = {int(value): index for index, value in enumerate(identifiers)}
        for row in found:
            row["SOURCE"] = "PUBMED"
            row["SOURCE_URL"] = f"https://pubmed.ncbi.nlm.nih.gov/{row['PUBMED_ID']}/"
        return sorted(found, key=lambda row: order.get(int(row["PUBMED_ID"]), 9999))

    @staticmethod
    def _clinical_trials(
        connection: Any,
        identifiers: list[int] | list[str],
    ) -> list[dict[str, Any]]:
        placeholders = ", ".join(["%s"] * len(identifiers))
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT NCT_ID, OFFICIAL_TITLE, BRIEF_TITLE, START_DATE,
                       OVERALL_STATUS, PHASE, STUDY_TYPE, MESH_TERM, UPDATE_DATE
                FROM COMPILE_ADD_ON.CLINICAL_TRIAL_DETAILS.STUDIES
                WHERE NCT_ID IN ({placeholders})
                """,
                tuple(identifiers),
            )
            studies = _rows(cursor)

            related: dict[str, tuple[str, tuple[str, ...]]] = {
                "CONDITIONS": ("CONDITIONS", ("NAME",)),
                "INTERVENTIONS": (
                    "INTERVENTIONS",
                    ("NAME", "INTERVENTION_TYPE", "DESCRIPTION"),
                ),
                "SPONSORS": (
                    "SPONSORS",
                    ("NAME", "AGENCY_CLASS", "LEAD_OR_COLLABORATOR"),
                ),
                "REFERENCES": (
                    "REFERENCES",
                    ("PMID", "REFERENCE_TYPE", "CITATION"),
                ),
            }
            grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
                lambda: defaultdict(list)
            )
            for result_key, (table, columns) in related.items():
                selected = ", ".join(("NCT_ID", *columns))
                cursor.execute(
                    f"""
                    SELECT {selected}
                    FROM COMPILE_ADD_ON.CLINICAL_TRIAL_DETAILS.{table}
                    WHERE NCT_ID IN ({placeholders})
                    """,
                    tuple(identifiers),
                )
                for row in _rows(cursor):
                    nct_id = row.pop("NCT_ID")
                    grouped[nct_id][result_key].append(row)
        finally:
            cursor.close()

        order = {str(value): index for index, value in enumerate(identifiers)}
        for study in studies:
            nct_id = study["NCT_ID"]
            study.update(grouped[nct_id])
            study["SOURCE"] = "CLINICALTRIALS.GOV"
            study["SOURCE_URL"] = f"https://clinicaltrials.gov/study/{nct_id}"
        return sorted(studies, key=lambda row: order.get(row["NCT_ID"], 9999))
