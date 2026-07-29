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
    "news",
    "congresses",
    "competitor_analysis",
    "schema",
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
    "news",
    "congresses",
    "competitor_analysis",
    "schema",
)
DEFAULT_SOURCES = tuple(source for source in ALLOWED_SOURCES if source != "schema")
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
        sources = DEFAULT_SOURCES if source == "all" else (source,)
        results: list[dict[str, Any]] = []
        source_batches: list[list[dict[str, Any]]] = []
        errors: list[dict[str, str]] = []

        connection = self._connect()
        try:
            for selected_source in sources:
                try:
                    method = getattr(self, f"_search_{selected_source}")
                    batch = method(
                        connection,
                        query=query,
                        limit=safe_limit,
                        context_id=context_id,
                    )
                    if source == "all":
                        source_batches.append(batch)
                    else:
                        results.extend(batch)
                except Exception as exc:
                    errors.append(
                        {
                            "source": selected_source,
                            "error": type(exc).__name__,
                        }
                    )
        finally:
            connection.close()

        if source == "all":
            # ``top_k`` is a response-wide bound. Round-robin keeps an
            # all-source result diverse without returning top_k rows from
            # every adapter and overwhelming a GPT Action response.
            while len(results) < safe_limit:
                added = False
                for batch in source_batches:
                    if batch and len(results) < safe_limit:
                        results.append(batch.pop(0))
                        added = True
                if not added:
                    break

        latency_ms = int((time.perf_counter() - started) * 1000)
        return results[:safe_limit], errors, latency_ms

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

    def _search_news(
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
                "CATEGORY",
                "PUBLISHED_DATE",
                "PUBLICATION_INFO",
                "SEARCH_QUERY",
                "SNIPPET",
                "SOURCE",
                "TITLE",
            ),
            terms,
        )
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT NEWS_ID, CATEGORY, CITED_BY, PUBLISHED_DATE, LINK,
                       HTML_URL, PDF_URL, PUBLICATION_INFO, SEARCH_QUERY,
                       SNIPPET, SOURCE, TITLE, PUBLICATION_YEAR, SOURCE_FILE,
                       LOADED_AT
                FROM {DATABASE}.{SCHEMA}.NEWS
                WHERE {predicate}
                ORDER BY TRY_TO_DATE(PUBLISHED_DATE, 'MON DD, YYYY') DESC NULLS LAST,
                         LOADED_AT DESC, TITLE
                LIMIT {int(limit)}
                """,
                tuple(params),
            )
            rows = _rows(cursor)
        finally:
            cursor.close()
        return [
            _evidence(
                source_type="NEWS",
                record_id=row.get("NEWS_ID"),
                title=row.get("TITLE"),
                text=row.get("SNIPPET") or row.get("PUBLICATION_INFO"),
                url=row.get("LINK") or row.get("HTML_URL") or row.get("PDF_URL"),
                metadata={
                    key.lower(): value
                    for key, value in row.items()
                    if key not in {"NEWS_ID", "TITLE", "SNIPPET", "PUBLICATION_INFO"}
                },
            )
            for row in rows
        ]

    def _search_competitor_analysis(
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
                "s.SHEET_NAME",
                "s.SECTION_TITLE",
                "s.SECTION_DESCRIPTION",
                "c.CELL_VALUE",
                "c.FORMULA",
            ),
            terms,
        )
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                WITH MATCHING_ROWS AS (
                    SELECT c.WORKBOOK_ID, c.SECTION_ID, c.ROW_NUMBER
                    FROM {DATABASE}.{SCHEMA}.COMPETITOR_ANALYSIS_CELLS c
                    JOIN {DATABASE}.{SCHEMA}.COMPETITOR_ANALYSIS_SECTIONS s
                      ON s.SECTION_ID = c.SECTION_ID
                    WHERE {predicate}
                    GROUP BY c.WORKBOOK_ID, c.SECTION_ID, c.ROW_NUMBER
                )
                SELECT w.SOURCE_FILE, s.SHEET_NAME, s.SECTION_TITLE,
                       s.SECTION_DESCRIPTION, c.SECTION_ID, c.ROW_NUMBER,
                       LISTAGG(
                           CONCAT(c.CELL_COORDINATE, ': ',
                                  COALESCE(c.CELL_VALUE, c.FORMULA, '')),
                           ' | '
                       ) WITHIN GROUP (ORDER BY c.COLUMN_NUMBER) AS ROW_TEXT
                FROM MATCHING_ROWS m
                JOIN {DATABASE}.{SCHEMA}.COMPETITOR_ANALYSIS_WORKBOOKS w
                  ON w.WORKBOOK_ID = m.WORKBOOK_ID
                JOIN {DATABASE}.{SCHEMA}.COMPETITOR_ANALYSIS_SECTIONS s
                  ON s.SECTION_ID = m.SECTION_ID
                JOIN {DATABASE}.{SCHEMA}.COMPETITOR_ANALYSIS_CELLS c
                  ON c.SECTION_ID = m.SECTION_ID
                 AND c.ROW_NUMBER = m.ROW_NUMBER
                GROUP BY w.SOURCE_FILE, s.SORT_ORDER, s.SHEET_NAME,
                         s.SECTION_TITLE, s.SECTION_DESCRIPTION,
                         c.SECTION_ID, c.ROW_NUMBER
                ORDER BY s.SORT_ORDER, c.ROW_NUMBER
                LIMIT {int(limit)}
                """,
                tuple(params),
            )
            rows = _rows(cursor)
        finally:
            cursor.close()
        return [
            _evidence(
                source_type="COMPETITOR_ANALYSIS",
                record_id=f"{row.get('SECTION_ID')}:{row.get('ROW_NUMBER')}",
                title=(
                    f"{row.get('SHEET_NAME')} row {row.get('ROW_NUMBER')}"
                ),
                text=row.get("ROW_TEXT"),
                metadata={
                    "source_file": row.get("SOURCE_FILE"),
                    "sheet_name": row.get("SHEET_NAME"),
                    "section_title": row.get("SECTION_TITLE"),
                    "section_description": row.get("SECTION_DESCRIPTION"),
                    "row_number": row.get("ROW_NUMBER"),
                },
            )
            for row in rows
        ]

    def _search_congresses(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        del context_id
        terms = [
            term
            for term in query_terms(query)
            if term
            not in {
                "asundexian",
                "milvexian",
                "bay2433334",
                "bms-986177",
                "jnj-70033093",
            }
        ]
        if not terms:
            terms = ["congress"]
        metadata_columns = (
            "c.CONFERENCE",
            "c.DATE_DISPLAY",
            "c.PLACE",
            "w.PAGE_TITLE",
            "w.META_DESCRIPTION",
        )
        metadata_blob = "CONCAT_WS(' | ', " + ", ".join(
            f"COALESCE(TO_VARCHAR({column}), '')" for column in metadata_columns
        ) + ")"
        content_blob = "LEFT(COALESCE(w.CONTENT_TEXT, ''), 50000)"
        patterns = [f"%{term}%" for term in terms]
        match_score = " + ".join(
            (
                f"(IFF({metadata_blob} ILIKE %s, 5, 0) + "
                f"IFF({content_blob} ILIKE %s, 1, 0))"
            )
            for _ in terms
        )
        predicate = " OR ".join(
            (
                f"({metadata_blob} ILIKE %s OR "
                f"{content_blob} ILIKE %s)"
            )
            for _ in terms
        )
        scored_params = [
            pattern
            for pattern in patterns
            for _ in range(2)
        ]
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT w.CONTENT_ID, c.CONGRESS_ID, c.CONFERENCE,
                       c.START_DATE, c.END_DATE, c.DATE_DISPLAY, c.PLACE,
                       w.PAGE_URL, w.PAGE_TITLE, w.META_DESCRIPTION,
                       LEFT(w.CONTENT_TEXT, 12000) AS CONTENT_TEXT,
                       w.CONTENT_HASH, w.CRAWL_DEPTH, w.SCRAPED_AT,
                       ({match_score}) AS MATCH_SCORE
                FROM {DATABASE}.{SCHEMA}.CONGRESSES c
                JOIN {DATABASE}.{SCHEMA}.CONGRESS_WEB_CONTENT w
                  ON w.CONGRESS_ID = c.CONGRESS_ID
                WHERE w.CONTENT_TEXT IS NOT NULL
                  AND {predicate}
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY w.CONTENT_HASH
                    ORDER BY w.CRAWL_DEPTH, w.PAGE_URL
                ) = 1
                ORDER BY MATCH_SCORE DESC, c.START_DATE,
                         w.CRAWL_DEPTH, w.PAGE_URL
                LIMIT {int(limit)}
                """,
                tuple(scored_params + scored_params),
            )
            rows = _rows(cursor)
        finally:
            cursor.close()
        return [
            _evidence(
                source_type="CONGRESS",
                record_id=row.get("CONTENT_ID"),
                title=row.get("PAGE_TITLE") or row.get("CONFERENCE"),
                text=row.get("CONTENT_TEXT") or row.get("META_DESCRIPTION"),
                url=row.get("PAGE_URL"),
                metadata={
                    "congress_id": row.get("CONGRESS_ID"),
                    "conference": row.get("CONFERENCE"),
                    "start_date": row.get("START_DATE"),
                    "end_date": row.get("END_DATE"),
                    "dates": row.get("DATE_DISPLAY"),
                    "place": row.get("PLACE"),
                    "content_hash": row.get("CONTENT_HASH"),
                    "crawl_depth": row.get("CRAWL_DEPTH"),
                    "scraped_at": row.get("SCRAPED_AT"),
                },
            )
            for row in rows
        ]

    def _search_schema(
        self,
        connection: Any,
        *,
        query: str,
        limit: int,
        context_id: str | None,
    ) -> list[dict[str, Any]]:
        """Search every APERTURECI table/view without accepting identifiers."""
        del context_id
        terms = query_terms(query)
        if not terms:
            return []
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION
                FROM {DATABASE}.INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND DATA_TYPE NOT IN ('BINARY', 'VARBINARY', 'VECTOR')
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """,
                (SCHEMA,),
            )
            catalog_rows = _rows(cursor)
        finally:
            cursor.close()

        columns_by_table: dict[str, list[str]] = {}
        for row in catalog_rows:
            columns_by_table.setdefault(str(row["TABLE_NAME"]), []).append(
                str(row["COLUMN_NAME"])
            )

        results: list[dict[str, Any]] = []
        for table_name, columns in columns_by_table.items():
            if len(results) >= limit:
                break
            selected_columns = columns[:30]
            quoted = [f'"{column.replace(chr(34), chr(34) * 2)}"' for column in selected_columns]
            blob = "CONCAT_WS(' | ', " + ", ".join(
                f"COALESCE(TO_VARCHAR({column}), '')" for column in quoted
            ) + ")"
            predicates = [f"{blob} ILIKE %s" for _ in terms]
            object_args = ", ".join(
                f"'{column.replace(chr(39), chr(39) * 2)}', {quoted_column}"
                for column, quoted_column in zip(selected_columns, quoted)
            )
            table_identifier = table_name.replace('"', '""')
            table_cursor = connection.cursor()
            try:
                table_cursor.execute(
                    f"""
                    SELECT SHA2({blob}, 256) AS RECORD_ID,
                           {blob} AS ROW_TEXT,
                           OBJECT_CONSTRUCT_KEEP_NULL({object_args}) AS ROW_DATA
                    FROM {DATABASE}.{SCHEMA}."{table_identifier}"
                    WHERE {" OR ".join(predicates)}
                    LIMIT 1
                    """,
                    tuple(f"%{term}%" for term in terms),
                )
                rows = _rows(table_cursor)
            except Exception:
                rows = []
            finally:
                table_cursor.close()
            for row in rows:
                results.append(
                    _evidence(
                        source_type="SCHEMA_ROW",
                        record_id=f"{table_name}:{row.get('RECORD_ID')}",
                        title=table_name,
                        text=row.get("ROW_TEXT"),
                        metadata={
                            "table_name": table_name,
                            "row_data": row.get("ROW_DATA"),
                        },
                    )
                )
        return results[:limit]
