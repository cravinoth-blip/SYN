"""Snowflake Cortex Search client for the Knowledge Hub Render API."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


DEFAULT_RESULT_COLUMNS = (
    "CHUNK_ID",
    "CHUNK_TEXT",
    "DOCUMENT_ID",
    "VERSION",
    "COLLECTION_ID",
    "TITLE",
    "PAGE_FROM",
    "PAGE_TO",
    "SECTION_PATH",
    "DOCUMENT_TYPE",
    "LANGUAGE",
    "ORIGINAL_FILENAME",
    "STAGE_RELATIVE_PATH",
    "EVIDENCE_TYPE",
    "IMAGE_ID",
    "IMAGE_STAGE_RELATIVE_PATH",
)


class ConfigurationError(RuntimeError):
    """Raised when required Snowflake configuration is absent or invalid."""


@dataclass(frozen=True)
class SearchSettings:
    account: str
    user: str
    warehouse: str
    database: str
    schema: str
    service: str
    role: str | None
    private_key_path: Path
    private_key_passphrase: str | None

    @classmethod
    def from_environment(cls) -> "SearchSettings":
        account = os.getenv("SNOWFLAKE_ACCOUNT", "").strip()
        user = os.getenv("SNOWFLAKE_USER", "").strip()
        missing = [
            name
            for name, value in (
                ("SNOWFLAKE_ACCOUNT", account),
                ("SNOWFLAKE_USER", user),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        key_path = Path(
            os.getenv(
                "SNOWFLAKE_PRIVATE_KEY_PATH",
                "/etc/secrets/private_key.pem",
            )
        )
        if not key_path.is_file():
            raise ConfigurationError(
                f"Snowflake private key was not found at {key_path}"
            )

        return cls(
            account=account,
            user=user,
            warehouse=os.getenv(
                "SNOWFLAKE_WAREHOUSE", "WH_COMMUNICATIONS__EU__DER"
            ).strip(),
            database=os.getenv(
                "SNOWFLAKE_DATABASE", "COMMUNICATIONS__EU__DER__DEV"
            ).strip(),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "KNOWLEDGE_HUB").strip(),
            service=os.getenv("SNOWFLAKE_CORTEX_SEARCH_SERVICE", "KNOWLEDGE_SEARCH").strip(),
            # Use the key-pair service user's authorized default role. An explicit
            # Render role can make an otherwise valid connection fail before search.
            role=None,
            private_key_path=key_path,
            private_key_passphrase=(
                os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "").strip() or None
            ),
        )

    @property
    def qualified_service_name(self) -> str:
        return f"{self.database}.{self.schema}.{self.service}"


def build_filter(
    *,
    collection_id: str | None = None,
    language: str | None = None,
    document_type: str | None = None,
    evidence_type: str | None = None,
) -> dict[str, Any] | None:
    """Build a Cortex Search filter from an explicit allow-list of attributes."""
    clauses = [
        {"@eq": {field: value}}
        for field, value in (
            ("COLLECTION_ID", collection_id),
            ("LANGUAGE", language),
            ("DOCUMENT_TYPE", document_type),
            ("EVIDENCE_TYPE", evidence_type),
        )
        if value
    ]
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"@and": clauses}


def _load_private_key(settings: SearchSettings) -> bytes:
    from cryptography.hazmat.primitives import serialization

    pem_bytes = settings.private_key_path.read_bytes()
    password = (
        settings.private_key_passphrase.encode()
        if settings.private_key_passphrase
        else None
    )
    private_key = serialization.load_pem_private_key(
        pem_bytes,
        password=password,
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _normalise_response(response: Any) -> list[dict[str, Any]]:
    if hasattr(response, "to_json"):
        payload = json.loads(response.to_json())
    elif isinstance(response, str):
        payload = json.loads(response)
    elif isinstance(response, dict):
        payload = response
    else:
        payload = {"results": getattr(response, "results", [])}

    results = payload.get("results", [])
    if not isinstance(results, list):
        return []
    return [
        {str(key).upper(): value for key, value in row.items()}
        for row in results
        if isinstance(row, dict)
    ]


class KnowledgeSearchClient:
    """Execute low-latency Cortex Search queries with key-pair authentication."""

    def __init__(self, settings: SearchSettings):
        self.settings = settings

    def search(
        self,
        *,
        query: str,
        limit: int,
        collection_id: str | None = None,
        language: str | None = None,
        document_type: str | None = None,
        evidence_type: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        import snowflake.connector
        from snowflake.core import Root

        connect_args: dict[str, Any] = {
            "account": self.settings.account,
            "user": self.settings.user,
            "private_key": _load_private_key(self.settings),
            "warehouse": self.settings.warehouse,
            "database": self.settings.database,
            "schema": self.settings.schema,
            "application": "KNOWLEDGE_HUB_RENDER_API",
        }
        if self.settings.role:
            connect_args["role"] = self.settings.role

        started = time.perf_counter()
        connection = snowflake.connector.connect(**connect_args)
        try:
            root = Root(connection)
            service = (
                root.databases[self.settings.database]
                .schemas[self.settings.schema]
                .cortex_search_services[self.settings.service]
            )
            search_filter = build_filter(
                collection_id=collection_id,
                language=language,
                document_type=document_type,
                evidence_type=evidence_type,
            )
            search_args: dict[str, Any] = {
                "query": query,
                "columns": list(DEFAULT_RESULT_COLUMNS),
                "limit": limit,
            }
            if search_filter:
                search_args["filter"] = search_filter
            try:
                response = service.search(**search_args)
                results = _normalise_response(response)
            except Exception as sdk_error:
                logger.warning(
                    "Cortex SDK search failed; retrying with SEARCH_PREVIEW: %s",
                    type(sdk_error).__name__,
                )
                preview_request = json.dumps(search_args)
                safe_service = self.settings.service.replace("'", "''")
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        "SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW("
                        f"'{safe_service}', %s)",
                        (preview_request,),
                    )
                    raw_response = cursor.fetchone()[0]
                    results = _normalise_response(raw_response)
                finally:
                    cursor.close()
        finally:
            connection.close()

        latency_ms = int((time.perf_counter() - started) * 1000)
        return results, latency_ms
