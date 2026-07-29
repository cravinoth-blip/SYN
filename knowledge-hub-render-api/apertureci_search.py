"""Governed retrieval across fixed APERTURECI evidence surfaces."""

from __future__ import annotations

import re
import time
from typing import Any, Literal

from knowledge_search import SearchSettings, _load_private_key, _normalise_response


ApertureSource = Literal[
    "all",
    "dexi",
    "publications",
    "clinical_trials",
    "competitor_maps",
    "trial_comparisons",
    "knowledge",
]

DATABASE = "COMMUNICATIONS__EU__DER__DEV"
SCHEMA = "APERTURECI"
PRIMARY_ASSET = "ASUNDEXIAN"
SOLE_COMPETITOR = "MILVEXIAN"
SCOPE_TERMS = (
    "asundexian",
    "bay 2433334",
    "bay2433334",
    "milvexian",
    "bms-986177",
    "bms 986177",
    "jnj-70033093",
    "jnj 70033093",
)
ALLOWED_SOURCES = (
    "dexi",
    "publications",
    "clinical_trials",
    "competitor_maps",
    "trial_comparisons",
    "knowledge",
)
STOP_WORDS = {
    "about",
    "and",
    "are",
    "for",
    "from",
    "into",
    "of",
    "on",
    "or",
    "the",
    "their",
    "to",
    "what",
    "with",
}


def query_terms(query: str) -> list[str]:
    """Return a bounded set of useful terms for structured-table matching."""
    terms: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9+./_-]*", query):
        term = raw.strip("._-/").lower()
        if len(term) < 3 or term in STOP_WORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms[:10]


def validate_scope_query(query: str) -> str:
    """Reject requests that do not identify the fixed asset comparison."""
    normalized = " ".join(query.lower().split())
    if not any(term in normalized for term in SCOPE_TERMS):
        raise ValueError(
            "APERTURECI only supports ASUNDEXIAN and MILVEXIAN. "
            "Include at least one of those assets in query_text."
        )
    return query.strip()


def _rows(cursor: Any) -> list[dict[str, Any]]:
    columns = [str(item[0]).upper() for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _like_predicate(columns: tuple[str, ...], terms: list[str]) -> tuple[str, list[str]]:
    blob = "CONCAT_WS(' | ', " + ", ".join(
        f"COALESCE(TO_VARCHAR({column}), '')" for column in columns
    ) + ")"
    predicates = [f"{blob} ILIKE %s" for _ in terms]
    return "(" + " OR ".join(predicates) + ")", [f"%{term}%" for term in terms]


def _evidence(
    *,
    source_type: str,
    record_id: Any,
    title: Any,
    text: Any,
    url: Any = None,
    context_id: Any = None,
    metadata: dict[str, Any] | None = None,
    score: Any = None,
) -> dict[str, Any]:
    item = {
        "SOURCE_TYPE": source_type,
        "RECORD_ID": str(record_id or ""),
        "TITLE": str(title or ""),
        "TEXT": str(text or ""),
        "URL": str(url or ""),
        "CONTEXT_ID": str(context_id or ""),
        "METADATA": metadata or {},
    }
    if score is not None:
        item["SCORE"] = score
    return item


class ApertureCISearchClient:
    """Search APERTURECI without accepting arbitrary SQL identifiers."""

    def __init__(self, settings: SearchSettings):
        self.settings = settings

    def _connect(self) -> Any:
        import snowflake.connector

        args: dict[str, Any] = {
            "account": self.settings.account,
            "user": self.settings.user,
            "private_key": _load_private_key(self.settings),
            "warehouse": self.settings.warehouse,
            "database": DATABASE,
            "schema": SCHEMA,
            "application": "APERTURECI_CUSTOM_GPT_API",
            "session_parameters": {"STATEMENT_TIMEOUT_IN_SECONDS": 45},
        }
        if self.settings.role:
            args["role"] = self.settings.role
        return snowflake.connector.connect(**args)

    def search(
        self,
        *,
        source: ApertureSource,
        query: str,
        limit: int,
        context_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
        started = time.perf_counter()
        query = validate_scope_query(query)
        if source != "all" and source not in ALLOWED_SOURCES:
            raise ValueError(f"Unsupported APERTURECI source: {source}")
        safe_limit = max(1, min(int(limit), 8))
        sources = ALLOWED_SOURCES if source == "all" else (source,)
        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        connection = self._connect()
        try:
            for selected_source in sources:
                try:
                    method = getattr(self, f"_search_{selected_source}")
                    results.extend(
                        method(
                            connection,
                            query=query,
                            limit=safe_limit,
                            context_id=context_id,
                        )
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "source": selected_source,
                            "error": type(exc).__name__,
                        }
                    )
        finally:
            connection.close()

        latency_ms = int((time.perf_counter() - started) * 1000)
        return results, errors, latency_ms

    @staticmethod
    def _cortex_search(
        connection: Any,
        *,
        service_name: str,
        query: str,
        columns: list[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        from snowflake.core import Root

        service = (
            Root(connection)
            .databases[DATABASE]
            .schemas[SCHEMA]
            .cortex_search_services[service_name]
        )
        response = service.search(query=query, columns=columns, limit=limit)
        return _normalise_response(response)

    def _search_dexi(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        del context_id
        rows = self._cortex_search(
            connection,
            service_name="DEXI_SEARCH",
            query=query,
            columns=[
                "DEXI_ID",
                "TITLE",
                "DOI",
                "PUBLISHED",
                "PUBLISHED_YEAR",
                "SUMMARY",
                "CHUNK_TEXT",
                "PRODUCT_TAGS",
                "QUALITY_FLAGS",
                "SOURCE_FILE",
            ],
            limit=limit,
        )
        return [
            _evidence(
                source_type="DEXI",
                record_id=row.get("DEXI_ID"),
                title=row.get("TITLE"),
                text=row.get("CHUNK_TEXT") or row.get("SUMMARY"),
                url=f"https://doi.org/{row['DOI']}" if row.get("DOI") else "",
                metadata={
                    "published": row.get("PUBLISHED"),
                    "published_year": row.get("PUBLISHED_YEAR"),
                    "product_tags": row.get("PRODUCT_TAGS"),
                    "quality_flags": row.get("QUALITY_FLAGS"),
                    "source_file": row.get("SOURCE_FILE"),
                },
                score=row.get("@SCORES"),
            )
            for row in rows
        ]

    def _search_knowledge(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        del context_id
        rows = self._cortex_search(
            connection,
            service_name="KNOWLEDGE_SEARCH",
            query=query,
            columns=[
                "CHUNK_ID",
                "CHUNK_TEXT",
                "DOCUMENT_ID",
                "TITLE",
                "ORIGINAL_FILENAME",
                "PAGE_FROM",
                "PAGE_TO",
                "SECTION_PATH",
                "EVIDENCE_TYPE",
            ],
            limit=limit,
        )
        return [
            _evidence(
                source_type="KNOWLEDGE",
                record_id=row.get("CHUNK_ID"),
                title=row.get("TITLE") or row.get("ORIGINAL_FILENAME"),
                text=row.get("CHUNK_TEXT"),
                metadata={
                    "document_id": row.get("DOCUMENT_ID"),
                    "source_file": row.get("ORIGINAL_FILENAME"),
                    "page_from": row.get("PAGE_FROM"),
                    "page_to": row.get("PAGE_TO"),
                    "section_path": row.get("SECTION_PATH"),
                    "evidence_type": row.get("EVIDENCE_TYPE"),
                },
                score=row.get("@SCORES"),
            )
            for row in rows
        ]

    def _search_publications(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        terms = query_terms(query)
        if not terms:
            return []
        predicate, params = _like_predicate(
            (
                "SEARCH_DISEASE",
                "PRODUCT",
                "TRIAL",
                "PUBLICATION_TITLE",
                "SOURCE",
                "AUTHORS",
                "KEY_FINDING",
                "PMID",
                "SEARCH_QUERY",
            ),
            terms,
        )
        context_clause = "AND CONTEXT_ID = %s" if context_id else ""
        if context_id:
            params.append(context_id)
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT STAGING_ROW_ID, CONTEXT_ID, PRODUCT, TRIAL,
                       PUBLICATION_TITLE, SOURCE, PUBLICATION_TYPE,
                       PUBLICATION_YEAR, AUTHORS, KEY_FINDING, URL_DOI,
                       PUBMED_URL, PMID, SOURCE_STATUS, DISCOVERY_SOURCE,
                       IS_MISSING_FROM_SNOWFLAKE
                FROM {DATABASE}.{SCHEMA}.APERTURECI_TEMP_PUBLICATIONS
                WHERE {predicate}
                  {context_clause}
                ORDER BY TRY_TO_NUMBER(PUBLICATION_YEAR) DESC NULLS LAST,
                         SORT_ORDER, PUBLICATION_TITLE
                LIMIT {int(limit)}
                """,
                tuple(params),
            )
            rows = _rows(cursor)
        finally:
            cursor.close()
        return [
            _evidence(
                source_type="PUBLICATION",
                record_id=row["STAGING_ROW_ID"],
                title=row.get("PUBLICATION_TITLE"),
                text=row.get("KEY_FINDING"),
                url=row.get("PUBMED_URL") or row.get("URL_DOI"),
                context_id=row.get("CONTEXT_ID"),
                metadata={
                    "product": row.get("PRODUCT"),
                    "trial": row.get("TRIAL"),
                    "journal_or_source": row.get("SOURCE"),
                    "publication_type": row.get("PUBLICATION_TYPE"),
                    "publication_year": row.get("PUBLICATION_YEAR"),
                    "authors": row.get("AUTHORS"),
                    "pmid": row.get("PMID"),
                    "source_status": row.get("SOURCE_STATUS"),
                    "discovery_source": row.get("DISCOVERY_SOURCE"),
                    "missing_from_snowflake": row.get("IS_MISSING_FROM_SNOWFLAKE"),
                },
            )
            for row in rows
        ]

    def _search_clinical_trials(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        terms = query_terms(query)
        if not terms:
            return []
        predicate, params = _like_predicate(
            (
                "PRODUCT",
                "TRIAL",
                "NCT_ID",
                "DISEASE",
                "STATUS",
                "PHASE",
                "INTERVENTION",
                "COMPARATOR",
                "REGIMEN",
                "EFFICACY_SIGNAL",
                "SAFETY_SIGNAL",
                "RAW_SUMMARY",
            ),
            terms,
        )
        context_clause = "AND CONTEXT_ID = %s" if context_id else ""
        if context_id:
            params.append(context_id)
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT STAGING_ROW_ID, CONTEXT_ID, SOURCE_TABLE, PRODUCT, TRIAL,
                       NCT_ID, DISEASE, STATUS, PHASE, INTERVENTION, COMPARATOR,
                       REGIMEN, START_DATE, PRIMARY_COMPLETION_DATE,
                       COMPLETION_DATE, EFFICACY_SIGNAL, SAFETY_SIGNAL, RAW_SUMMARY
                FROM {DATABASE}.{SCHEMA}.APERTURECI_TEMP_CLINICAL_TRIALS
                WHERE {predicate}
                  {context_clause}
                ORDER BY SORT_ORDER, PRODUCT, TRIAL
                LIMIT {int(limit)}
                """,
                tuple(params),
            )
            rows = _rows(cursor)
        finally:
            cursor.close()
        return [
            _evidence(
                source_type="CLINICAL_TRIAL",
                record_id=row["STAGING_ROW_ID"],
                title=row.get("TRIAL") or row.get("NCT_ID") or row.get("PRODUCT"),
                text=" | ".join(
                    str(value)
                    for value in (
                        row.get("EFFICACY_SIGNAL"),
                        row.get("SAFETY_SIGNAL"),
                        row.get("RAW_SUMMARY"),
                    )
                    if value
                ),
                url=(
                    f"https://clinicaltrials.gov/study/{row['NCT_ID']}"
                    if row.get("NCT_ID")
                    else ""
                ),
                context_id=row.get("CONTEXT_ID"),
                metadata={
                    key.lower(): value
                    for key, value in row.items()
                    if key not in {"STAGING_ROW_ID", "CONTEXT_ID", "RAW_SUMMARY"}
                },
            )
            for row in rows
        ]

    def _search_competitor_maps(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        del context_id
        terms = query_terms(query)
        if not terms:
            return []
        predicate, params = _like_predicate(
            (
                "r.ASSET",
                "r.DISEASE",
                "r.GEOGRAPHY",
                "r.COMPANY",
                "c.NAME",
                "c.CANDIDATE",
                "c.QUADRANT",
                "c.THREAT_LEVEL",
                "c.RATIONALE",
                "p.MOA",
                "p.PHASE",
                "p.TRIAL",
                "p.NCT_ID",
                "p.EFFICACY",
                "p.SAFETY",
                "p.POSITIONING",
            ),
            terms,
        )
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT r.RUN_ID, r.ASSET, r.DISEASE, r.GEOGRAPHY, r.COMPANY,
                       r.CREATED_AT, c.COMPETITOR_ID, c.NAME, c.CANDIDATE,
                       c.QUADRANT, c.THREAT_LEVEL, c.RATIONALE,
                       p.MOA, p.MODALITY, p.ROA, p.DOSING, p.PHASE, p.TRIAL,
                       p.NCT_ID, p.LAUNCH, p.EFFICACY, p.SAFETY, p.POSITIONING
                FROM {DATABASE}.{SCHEMA}.COMPETITOR_MAP_RUNS r
                JOIN {DATABASE}.{SCHEMA}.COMPETITOR_MAP_COMPETITORS c
                  ON c.RUN_ID = r.RUN_ID
                LEFT JOIN {DATABASE}.{SCHEMA}.COMPETITOR_MAP_PIPELINE_ROWS p
                  ON p.RUN_ID = c.RUN_ID
                 AND p.COMPETITOR_ID = c.COMPETITOR_ID
                WHERE {predicate}
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY r.ASSET, r.DISEASE, c.COMPETITOR_ID
                    ORDER BY r.CREATED_AT DESC, p.SORT_ORDER
                ) = 1
                ORDER BY r.CREATED_AT DESC, c.SORT_ORDER
                LIMIT {int(limit)}
                """,
                tuple(params),
            )
            rows = _rows(cursor)
        finally:
            cursor.close()
        return [
            _evidence(
                source_type="COMPETITOR_MAP",
                record_id=f"{row['RUN_ID']}:{row['COMPETITOR_ID']}",
                title=row.get("CANDIDATE") or row.get("NAME"),
                text=" | ".join(
                    str(value)
                    for value in (
                        row.get("RATIONALE"),
                        row.get("EFFICACY"),
                        row.get("SAFETY"),
                        row.get("POSITIONING"),
                    )
                    if value
                ),
                url=(
                    f"https://clinicaltrials.gov/study/{row['NCT_ID']}"
                    if row.get("NCT_ID")
                    else ""
                ),
                metadata={
                    key.lower(): value
                    for key, value in row.items()
                    if key not in {"RATIONALE", "EFFICACY", "SAFETY", "POSITIONING"}
                },
            )
            for row in rows
        ]

    def _search_trial_comparisons(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        terms = query_terms(query)
        if not terms:
            return []
        predicate, params = _like_predicate(("TITLE", "TEXT"), terms)
        context_clause = "AND CONTEXT_ID = %s" if context_id else ""
        if context_id:
            params.append(context_id)
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                WITH RECORDS AS (
                    SELECT 'PRODUCT_PROGRAMME' AS SECTION,
                           PRODUCT_PROGRAMME_ROW_ID AS RECORD_ID, CONTEXT_ID,
                           PRODUCT AS TITLE,
                           CONCAT_WS(' | ', MODALITY_AND_TARGET, ROUTE_FREQUENCY,
                               PHARMACOLOGIC_CHARACTERISTICS, DEVELOPMENT_INDICATIONS,
                               KEY_TRIALS, CURRENT_EVIDENCE_POSITION) AS TEXT,
                           CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_PRODUCT_PROGRAMME_COMPARISON
                    UNION ALL
                    SELECT 'STUDY_DESIGN', STUDY_DESIGN_ROW_ID, CONTEXT_ID, TRIAL,
                           CONCAT_WS(' | ', PRODUCT, DESIGN, POPULATION, RANDOMIZATION,
                               COMPARATOR, REGIMEN, EXPOSURE, FOLLOW_UP, ANALYSIS_SETS,
                               STATISTICAL_HYPOTHESIS, EARLY_TERMINATION_STATUS), CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_STUDY_DESIGN_MATRIX
                    UNION ALL
                    SELECT 'ENDPOINT_DEFINITION', ENDPOINT_DEFINITION_ROW_ID, CONTEXT_ID,
                           CONCAT_WS(' - ', TRIAL, ENDPOINT),
                           CONCAT_WS(' | ', PRODUCT, ENDPOINT_TYPE, VERBATIM_DEFINITION,
                               COMPONENTS, HIERARCHY, ASCERTAINMENT, ADJUDICATION,
                               ANALYSIS_WINDOW, STATISTICAL_METHOD), CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_ENDPOINT_DEFINITION_MATRIX
                    UNION ALL
                    SELECT 'EFFICACY', EFFICACY_RESULT_ROW_ID, CONTEXT_ID,
                           CONCAT_WS(' - ', TRIAL, ENDPOINT),
                           CONCAT_WS(' | ', ARM, STATUS, EVENTS_N, PERCENT_VALUE, RATE,
                               EFFECT_MEASURE, ESTIMATE, CI_95, P_VALUE, ANALYSIS_SET,
                               TIME_WINDOW), CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_COMPLETE_EFFICACY_RESULTS
                    UNION ALL
                    SELECT 'SAFETY', SAFETY_RESULT_ROW_ID, CONTEXT_ID,
                           CONCAT_WS(' - ', TRIAL, SAFETY_ENDPOINT),
                           CONCAT_WS(' | ', ARM, BLEEDING_DEFINITION, EVENTS_N,
                               PERCENT_VALUE, RATE, EFFECT_MEASURE, ESTIMATE, CI_95,
                               P_VALUE, ANALYSIS_SET, TIME_WINDOW, SAFETY_SIGNAL_NOTES),
                           CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_COMPLETE_SAFETY_RESULTS
                    UNION ALL
                    SELECT 'PKPD_DOSE_RESPONSE', PKPD_ROW_ID, CONTEXT_ID,
                           CONCAT_WS(' - ', PRODUCT, TRIAL, DOSE),
                           CONCAT_WS(' | ', EXPOSURE, FXI_FXIA_SUPPRESSION, APTT_EFFECT,
                               ONSET_OFFSET, DOSE_RESPONSE_FINDING,
                               DOSE_SELECTION_OR_ABANDONMENT_RATIONALE), CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_PKPD_DOSE_RESPONSE
                    UNION ALL
                    SELECT 'CROSS_TRIAL', CROSS_TRIAL_ROW_ID, CONTEXT_ID,
                           COMPARISON_DOMAIN,
                           CONCAT_WS(' | ', COMMON_FEATURE, MATERIAL_DIFFERENCES,
                               WHY_THE_DIFFERENCE_MATTERS,
                               PERMISSIBILITY_OF_INDIRECT_COMPARISON, CAUTION_LEVEL),
                           CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_CROSS_TRIAL_COMPARISONS
                    UNION ALL
                    SELECT 'EVIDENCE_GAP', EVIDENCE_GAP_ROW_ID, CONTEXT_ID,
                           CONCAT_WS(' - ', PRODUCT, TRIAL, EVIDENCE_AREA),
                           CONCAT_WS(' | ', GAP_TYPE, DETAIL, IMPACT_ON_INTERPRETATION,
                               ACTION_NEEDED), CREATED_AT
                    FROM {DATABASE}.{SCHEMA}.TRIAL_EVIDENCE_GAPS
                )
                SELECT SECTION, RECORD_ID, CONTEXT_ID, TITLE, TEXT, CREATED_AT
                FROM RECORDS
                WHERE {predicate}
                  {context_clause}
                ORDER BY CREATED_AT DESC
                LIMIT {int(limit)}
                """,
                tuple(params),
            )
            rows = _rows(cursor)
        finally:
            cursor.close()
        return [
            _evidence(
                source_type="TRIAL_COMPARISON",
                record_id=row.get("RECORD_ID"),
                title=row.get("TITLE"),
                text=row.get("TEXT"),
                context_id=row.get("CONTEXT_ID"),
                metadata={
                    "section": row.get("SECTION"),
                    "created_at": row.get("CREATED_AT"),
                },
            )
            for row in rows
        ]
