"""Read-only access to structured PFIZER ANTIINF product intelligence."""

from __future__ import annotations

import time
from typing import Any

from knowledge_search import SearchSettings, _load_private_key


def _rows(cursor: Any) -> list[dict[str, Any]]:
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


class ProductIntelligenceClient:
    """Query only the four allow-listed PFIZER_ANTIINF product tables."""

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
            "application": "PFIZER_ANTIINF_CUSTOM_GPT_API",
            "session_parameters": {"STATEMENT_TIMEOUT_IN_SECONDS": 30},
        }
        if self.settings.role:
            args["role"] = self.settings.role
        connection = snowflake.connector.connect(**args)
        cursor = connection.cursor()
        try:
            cursor.execute("USE SECONDARY ROLES NONE")
            cursor.execute(
                "USE DATABASE COMMUNICATIONS__EU__DER__DEV"
            )
            cursor.execute("USE SCHEMA PFIZER_ANTIINF")
        finally:
            cursor.close()
        return connection

    def _query(self, sql: str, parameters: tuple[Any, ...] = ()) -> tuple[list[dict[str, Any]], int]:
        started = time.perf_counter()
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(sql, parameters)
            rows = _rows(cursor)
        finally:
            cursor.close()
            connection.close()
        return rows, int((time.perf_counter() - started) * 1000)

    def list_products(self, therapeutic_set: str | None = None) -> tuple[list[dict[str, Any]], int]:
        where = "WHERE C.THERAPEUTIC_SET = %s" if therapeutic_set else ""
        parameters: tuple[Any, ...] = (therapeutic_set,) if therapeutic_set else ()
        return self._query(
            f"""
            WITH TRIAL_COUNTS AS (
                SELECT PRODUCT_KEY, COUNT(*) AS TRIAL_COUNT
                FROM PRODUCT_CLINICAL_TRIALS
                GROUP BY PRODUCT_KEY
            ), PUBLICATION_COUNTS AS (
                SELECT PRODUCT_KEY,
                       COUNT(*) AS PUBLICATION_AUTHOR_ROW_COUNT,
                       COUNT(DISTINCT PUBMED_ID) AS DISTINCT_PMID_COUNT
                FROM PRODUCT_TRIAL_PUBLICATIONS
                GROUP BY PRODUCT_KEY
            )
            SELECT C.PRODUCT_KEY, C.DISPLAY_NAME, C.REQUESTED_NAME,
                   C.ACTIVE_INGREDIENTS, C.PRODUCT_TYPE, C.THERAPEUTIC_SET,
                   C.MATCH_TERMS, C.SOURCE_DATABASE, C.SOURCE_NOTE,
                   COALESCE(T.TRIAL_COUNT, 0) AS TRIAL_COUNT,
                   COALESCE(P.DISTINCT_PMID_COUNT, 0) AS DISTINCT_PMID_COUNT,
                   COALESCE(P.PUBLICATION_AUTHOR_ROW_COUNT, 0)
                       AS PUBLICATION_AUTHOR_ROW_COUNT,
                   C.UPDATED_AT
            FROM PRODUCT_CATALOG C
            LEFT JOIN TRIAL_COUNTS T ON T.PRODUCT_KEY = C.PRODUCT_KEY
            LEFT JOIN PUBLICATION_COUNTS P ON P.PRODUCT_KEY = C.PRODUCT_KEY
            {where}
            ORDER BY C.THERAPEUTIC_SET, C.DISPLAY_NAME
            """,
            parameters,
        )

    def product_trials(
        self,
        product_key: str,
        *,
        limit: int,
        offset: int,
        overall_status: str | None = None,
        phase: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        clauses = ["PRODUCT_KEY = %s"]
        parameters: list[Any] = [product_key]
        if overall_status:
            clauses.append("OVERALL_STATUS = %s")
            parameters.append(overall_status)
        if phase:
            clauses.append("PHASE = %s")
            parameters.append(phase)
        parameters.extend((limit, offset))
        return self._query(
            f"""
            SELECT PRODUCT_KEY, NCT_ID, OFFICIAL_TITLE, BRIEF_TITLE,
                   START_DATE, STUDY_FIRST_SUBMITTED_DATE, OVERALL_STATUS,
                   PHASE, STUDY_TYPE, MESH_TERM, INTERVENTIONS, CONDITIONS,
                   SPONSORS, TRIAL_REFERENCES, SOURCE_UPDATE_DATE,
                   SOURCE_DATABASE, UPDATED_AT,
                   CONCAT('https://clinicaltrials.gov/study/', NCT_ID) AS SOURCE_URL
            FROM PRODUCT_CLINICAL_TRIALS
            WHERE {' AND '.join(clauses)}
            ORDER BY START_DATE DESC NULLS LAST, NCT_ID
            LIMIT %s OFFSET %s
            """,
            tuple(parameters),
        )

    def product_publications(
        self,
        product_key: str,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._query(
            """
            SELECT PRODUCT_KEY, PUBMED_ID,
                   ARRAY_AGG(DISTINCT NCT_ID) AS NCT_IDS,
                   ANY_VALUE(ARTICLE_TITLE) AS ARTICLE_TITLE,
                   ANY_VALUE(ABSTRACT) AS ABSTRACT,
                   ANY_VALUE(JOURNAL_COUNTRY) AS JOURNAL_COUNTRY,
                   ANY_VALUE(JOURNAL_TITLE) AS JOURNAL_TITLE,
                   ANY_VALUE(PUBLICATION_YEAR) AS PUBLICATION_YEAR,
                   ANY_VALUE(PUBMED_PUB_YEAR) AS PUBMED_PUB_YEAR,
                   ANY_VALUE(LANGUAGE) AS LANGUAGE,
                   ANY_VALUE(MESH_TERMS) AS MESH_TERMS,
                   ARRAY_AGG(DISTINCT OBJECT_CONSTRUCT_KEEP_NULL(
                       'author_index', AUTHOR_INDEX,
                       'first_name', AUTHOR_FIRSTNAME,
                       'last_name', AUTHOR_LASTNAME,
                       'fore_name', AUTHOR_FORENAME,
                       'initials', AUTHOR_INITIALS,
                       'collective_name', AUTHOR_COLLECTIVE_NAME,
                       'affiliation', AUTHOR_AFFILIATION,
                       'identifier', AUTHOR_IDENTIFIER,
                       'identifier_source', AUTHOR_IDENTIFIER_SOURCE
                   )) AS AUTHORS,
                   ANY_VALUE(ARTICLE_IDENTIFIERS) AS ARTICLE_IDENTIFIERS,
                   ANY_VALUE(PUBMED_REFERENCES) AS PUBMED_REFERENCES,
                   MAX(SOURCE_UPDATE_DATE) AS SOURCE_UPDATE_DATE,
                   CONCAT('https://pubmed.ncbi.nlm.nih.gov/', PUBMED_ID, '/') AS SOURCE_URL
            FROM PRODUCT_TRIAL_PUBLICATIONS
            WHERE PRODUCT_KEY = %s
            GROUP BY PRODUCT_KEY, PUBMED_ID
            ORDER BY PUBLICATION_YEAR DESC NULLS LAST, PUBMED_ID DESC
            LIMIT %s OFFSET %s
            """,
            (product_key, limit, offset),
        )

    def trial(self, nct_id: str) -> tuple[list[dict[str, Any]], int]:
        return self._query(
            """
            SELECT T.PRODUCT_KEY, C.DISPLAY_NAME, C.THERAPEUTIC_SET,
                   T.NCT_ID, T.OFFICIAL_TITLE, T.BRIEF_TITLE, T.START_DATE,
                   T.STUDY_FIRST_SUBMITTED_DATE, T.OVERALL_STATUS, T.PHASE,
                   T.STUDY_TYPE, T.MESH_TERM, T.INTERVENTIONS, T.CONDITIONS,
                   T.SPONSORS, T.TRIAL_REFERENCES, T.SOURCE_UPDATE_DATE,
                   CONCAT('https://clinicaltrials.gov/study/', T.NCT_ID) AS SOURCE_URL
            FROM PRODUCT_CLINICAL_TRIALS T
            JOIN PRODUCT_CATALOG C ON C.PRODUCT_KEY = T.PRODUCT_KEY
            WHERE T.NCT_ID = %s
            ORDER BY C.DISPLAY_NAME
            """,
            (nct_id,),
        )

    def publication(self, pubmed_id: str) -> tuple[list[dict[str, Any]], int]:
        return self._query(
            """
            SELECT PUBMED_ID,
                   ARRAY_AGG(DISTINCT PRODUCT_KEY) AS PRODUCT_KEYS,
                   ARRAY_AGG(DISTINCT NCT_ID) AS NCT_IDS,
                   ANY_VALUE(ARTICLE_TITLE) AS ARTICLE_TITLE,
                   ANY_VALUE(ABSTRACT) AS ABSTRACT,
                   ANY_VALUE(JOURNAL_COUNTRY) AS JOURNAL_COUNTRY,
                   ANY_VALUE(JOURNAL_TITLE) AS JOURNAL_TITLE,
                   ANY_VALUE(PUBLICATION_YEAR) AS PUBLICATION_YEAR,
                   ANY_VALUE(PUBMED_PUB_YEAR) AS PUBMED_PUB_YEAR,
                   ANY_VALUE(LANGUAGE) AS LANGUAGE,
                   ANY_VALUE(MESH_TERMS) AS MESH_TERMS,
                   ARRAY_AGG(DISTINCT OBJECT_CONSTRUCT_KEEP_NULL(
                       'author_index', AUTHOR_INDEX,
                       'first_name', AUTHOR_FIRSTNAME,
                       'last_name', AUTHOR_LASTNAME,
                       'fore_name', AUTHOR_FORENAME,
                       'initials', AUTHOR_INITIALS,
                       'collective_name', AUTHOR_COLLECTIVE_NAME,
                       'affiliation', AUTHOR_AFFILIATION,
                       'identifier', AUTHOR_IDENTIFIER,
                       'identifier_source', AUTHOR_IDENTIFIER_SOURCE
                   )) AS AUTHORS,
                   ANY_VALUE(ARTICLE_IDENTIFIERS) AS ARTICLE_IDENTIFIERS,
                   ANY_VALUE(PUBMED_REFERENCES) AS PUBMED_REFERENCES,
                   MAX(SOURCE_UPDATE_DATE) AS SOURCE_UPDATE_DATE,
                   CONCAT('https://pubmed.ncbi.nlm.nih.gov/', PUBMED_ID, '/') AS SOURCE_URL
            FROM PRODUCT_TRIAL_PUBLICATIONS
            WHERE PUBMED_ID = %s
            GROUP BY PUBMED_ID
            """,
            (pubmed_id,),
        )
