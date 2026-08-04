"""Safe schema-wide discovery and retrieval for PFIZER_ANTIINF."""

from __future__ import annotations

import time
from typing import Any

from knowledge_search import SearchSettings
from product_intelligence import ProductIntelligenceClient


DATABASE = "COMMUNICATIONS__EU__DER__DEV"
SCHEMA = "PFIZER_ANTIINF"
SEARCHABLE_TYPES = {
    "TEXT",
    "VARCHAR",
    "VARIANT",
    "ARRAY",
    "OBJECT",
}


def _rows(cursor: Any) -> list[dict[str, Any]]:
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


class SchemaBrowserClient:
    """Browse all tables/views in one fixed schema without accepting SQL."""

    def __init__(self, settings: SearchSettings):
        self.settings = settings

    def _connect(self) -> Any:
        return ProductIntelligenceClient(self.settings)._connect()

    @staticmethod
    def _object_metadata(connection: Any) -> dict[str, dict[str, Any]]:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT T.TABLE_NAME, T.TABLE_TYPE, T.ROW_COUNT, T.COMMENT,
                       C.COLUMN_NAME, C.DATA_TYPE, C.ORDINAL_POSITION
                FROM COMMUNICATIONS__EU__DER__DEV.INFORMATION_SCHEMA.TABLES T
                JOIN COMMUNICATIONS__EU__DER__DEV.INFORMATION_SCHEMA.COLUMNS C
                  ON C.TABLE_CATALOG = T.TABLE_CATALOG
                 AND C.TABLE_SCHEMA = T.TABLE_SCHEMA
                 AND C.TABLE_NAME = T.TABLE_NAME
                WHERE T.TABLE_SCHEMA = 'PFIZER_ANTIINF'
                ORDER BY T.TABLE_NAME, C.ORDINAL_POSITION
                """
            )
            metadata: dict[str, dict[str, Any]] = {}
            for row in _rows(cursor):
                item = metadata.setdefault(
                    row["TABLE_NAME"],
                    {
                        "TABLE_NAME": row["TABLE_NAME"],
                        "TABLE_TYPE": row["TABLE_TYPE"],
                        "ROW_COUNT": row["ROW_COUNT"],
                        "COMMENT": row["COMMENT"],
                        "COLUMNS": [],
                    },
                )
                item["COLUMNS"].append(
                    {
                        "COLUMN_NAME": row["COLUMN_NAME"],
                        "DATA_TYPE": row["DATA_TYPE"],
                        "ORDINAL_POSITION": row["ORDINAL_POSITION"],
                    }
                )
            return metadata
        finally:
            cursor.close()

    def objects(self) -> tuple[list[dict[str, Any]], int]:
        started = time.perf_counter()
        connection = self._connect()
        try:
            metadata = self._object_metadata(connection)
        finally:
            connection.close()
        return list(metadata.values()), int((time.perf_counter() - started) * 1000)

    def rows(
        self,
        table_name: str,
        *,
        limit: int,
        offset: int,
        search: str | None,
    ) -> tuple[list[dict[str, Any]], int]:
        started = time.perf_counter()
        connection = self._connect()
        try:
            metadata = self._object_metadata(connection)
            if table_name not in metadata:
                raise ValueError("Table or view is not in PFIZER_ANTIINF")
            columns = metadata[table_name]["COLUMNS"]
            searchable = [
                column["COLUMN_NAME"]
                for column in columns
                if column["DATA_TYPE"] in SEARCHABLE_TYPES
            ]
            qualified = (
                f"{_quote_identifier(DATABASE)}.{_quote_identifier(SCHEMA)}."
                f"{_quote_identifier(table_name)}"
            )
            params: list[Any] = []
            where = ""
            if search:
                if not searchable:
                    return [], int((time.perf_counter() - started) * 1000)
                haystack = ", ".join(
                    f"COALESCE(TO_VARCHAR({_quote_identifier(column)}), '')"
                    for column in searchable
                )
                where = f"WHERE CONCAT_WS(' ', {haystack}) ILIKE %s"
                params.append(f"%{search}%")
            params.extend((limit, offset))
            cursor = connection.cursor()
            try:
                cursor.execute(
                    f"""
                    SELECT OBJECT_CONSTRUCT_KEEP_NULL(*) AS RECORD
                    FROM {qualified}
                    {where}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                results = _rows(cursor)
            finally:
                cursor.close()
        finally:
            connection.close()
        return results, int((time.perf_counter() - started) * 1000)

    def search(
        self,
        query: str,
        *,
        table_names: list[str] | None,
        per_table_limit: int,
        total_limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        started = time.perf_counter()
        connection = self._connect()
        try:
            metadata = self._object_metadata(connection)
            selected = table_names or list(metadata)
            unknown = sorted(set(selected) - set(metadata))
            if unknown:
                raise ValueError(
                    "Objects are not in PFIZER_ANTIINF: " + ", ".join(unknown)
                )
            branches: list[str] = []
            params: list[Any] = []
            for table_name in selected:
                searchable = [
                    column["COLUMN_NAME"]
                    for column in metadata[table_name]["COLUMNS"]
                    if column["DATA_TYPE"] in SEARCHABLE_TYPES
                ]
                if not searchable:
                    continue
                haystack = ", ".join(
                    f"COALESCE(TO_VARCHAR({_quote_identifier(column)}), '')"
                    for column in searchable
                )
                qualified = (
                    f"{_quote_identifier(DATABASE)}.{_quote_identifier(SCHEMA)}."
                    f"{_quote_identifier(table_name)}"
                )
                safe_label = table_name.replace("'", "''")
                branches.append(
                    f"""
                    (SELECT '{safe_label}' AS TABLE_NAME,
                            OBJECT_CONSTRUCT_KEEP_NULL(*) AS RECORD
                     FROM {qualified}
                     WHERE CONCAT_WS(' ', {haystack}) ILIKE %s
                     LIMIT %s)
                    """
                )
                params.extend((f"%{query}%", per_table_limit))
            if not branches:
                return [], int((time.perf_counter() - started) * 1000)
            params.append(total_limit)
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "SELECT * FROM ("
                    + " UNION ALL ".join(branches)
                    + ") LIMIT %s",
                    tuple(params),
                )
                results = _rows(cursor)
            finally:
                cursor.close()
        finally:
            connection.close()
        return results, int((time.perf_counter() - started) * 1000)
