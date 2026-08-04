"""Render-hosted API for the isolated PFIZER ANTIINF Cortex Search service."""

from __future__ import annotations

import hmac
import os
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from knowledge_search import ConfigurationError, KnowledgeSearchClient, SearchSettings
from product_intelligence import ProductIntelligenceClient
from schema_browser import SchemaBrowserClient


app = FastAPI(
    title="PFIZER ANTIINF Search API",
    version="1.0.0",
    description=(
        "Secure API restricted to COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF."
    ),
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4_000)
    limit: int = Field(default=12, ge=1, le=50)
    collection_id: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, max_length=50)
    document_type: str | None = Field(default=None, max_length=100)
    evidence_type: str | None = Field(default=None, max_length=100)


class CompatibleQueryRequest(BaseModel):
    """Compatibility shape for the existing Render/GPT Action endpoint."""

    model_config = ConfigDict(extra="forbid")

    query_text: str = Field(min_length=1, max_length=4_000)
    top_k: int = Field(default=12, ge=1, le=50)
    collection_id: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, max_length=50)
    document_type: str | None = Field(default=None, max_length=100)
    evidence_type: str | None = Field(default=None, max_length=100)


class SchemaSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=200)
    table_names: list[str] | None = Field(default=None, max_length=15)
    per_table_limit: int = Field(default=3, ge=1, le=5)
    total_limit: int = Field(default=30, ge=1, le=50)


@lru_cache(maxsize=1)
def get_client() -> KnowledgeSearchClient:
    return KnowledgeSearchClient(SearchSettings.from_environment())


@lru_cache(maxsize=1)
def get_product_client() -> ProductIntelligenceClient:
    return ProductIntelligenceClient(SearchSettings.from_environment())


@lru_cache(maxsize=1)
def get_schema_browser() -> SchemaBrowserClient:
    return SchemaBrowserClient(SearchSettings.from_environment())


def require_api_key(
    supplied_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    expected_key = os.getenv("PFIZER_ANTIINF_API_KEY", "")
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PFIZER_ANTIINF_API_KEY is not configured",
        )
    if not supplied_key or not hmac.compare_digest(supplied_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


def execute_search(request: SearchRequest) -> dict:
    try:
        client = get_client()
        results, latency_ms = client.search(
            query=request.query,
            limit=request.limit,
            collection_id=request.collection_id,
            language=request.language,
            document_type=request.document_type,
            evidence_type=request.evidence_type,
        )
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Snowflake Cortex Search failed: {type(exc).__name__}",
        ) from exc

    return {
        "query": request.query,
        "result_count": len(results),
        "latency_ms": latency_ms,
        "results": results,
    }


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metadata", dependencies=[Depends(require_api_key)], tags=["operations"])
def metadata() -> dict:
    try:
        settings = SearchSettings.from_environment()
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return {
        "database": settings.database,
        "schema": settings.schema,
        "cortex_search_service": settings.service,
        "qualified_service": settings.qualified_service_name,
        "source_table": f"{settings.database}.{settings.schema}.KNOWLEDGE_CHUNKS",
        "product_tables": [
            f"{settings.database}.{settings.schema}.PRODUCT_CATALOG",
            f"{settings.database}.{settings.schema}.PRODUCT_CLINICAL_TRIALS",
            f"{settings.database}.{settings.schema}.PRODUCT_TRIAL_PUBLICATIONS",
            f"{settings.database}.{settings.schema}.PRODUCT_INTELLIGENCE_LOADS",
        ],
        "cross_database_access_enabled": False,
        "arbitrary_sql_enabled": False,
    }


@app.post("/search", dependencies=[Depends(require_api_key)], tags=["search"])
def search(request: SearchRequest) -> dict:
    return execute_search(request)


@app.post("/query/", dependencies=[Depends(require_api_key)], tags=["search"])
def compatible_query(request: CompatibleQueryRequest) -> dict:
    response = execute_search(
        SearchRequest(
            query=request.query_text,
            limit=request.top_k,
            collection_id=request.collection_id,
            language=request.language,
            document_type=request.document_type,
            evidence_type=request.evidence_type,
        )
    )
    return {"context": response["results"], **response}


def execute_product_query(operation) -> tuple[list[dict], int]:
    try:
        return operation()
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Snowflake product query failed: {type(exc).__name__}",
        ) from exc


def execute_schema_query(operation) -> tuple[list[dict], int]:
    try:
        return operation()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"PFIZER_ANTIINF schema query failed: {type(exc).__name__}",
        ) from exc


@app.get(
    "/schema/objects",
    dependencies=[Depends(require_api_key)],
    tags=["schema browser"],
)
def schema_objects() -> dict:
    results, latency_ms = execute_schema_query(lambda: get_schema_browser().objects())
    return {
        "database": "COMMUNICATIONS__EU__DER__DEV",
        "schema": "PFIZER_ANTIINF",
        "object_count": len(results),
        "latency_ms": latency_ms,
        "objects": results,
    }


@app.get(
    "/schema/tables/{table_name}/rows",
    dependencies=[Depends(require_api_key)],
    tags=["schema browser"],
)
def schema_table_rows(
    table_name: Annotated[str, Path(pattern=r"^[A-Za-z0-9_]+$", max_length=255)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> dict:
    name = table_name.upper()
    results, latency_ms = execute_schema_query(
        lambda: get_schema_browser().rows(
            name, limit=limit, offset=offset, search=search
        )
    )
    return {
        "table_name": name,
        "result_count": len(results),
        "limit": limit,
        "offset": offset,
        "latency_ms": latency_ms,
        "rows": results,
    }


@app.post(
    "/schema/search",
    dependencies=[Depends(require_api_key)],
    tags=["schema browser"],
)
def schema_search(request: SchemaSearchRequest) -> dict:
    table_names = (
        [name.upper() for name in request.table_names]
        if request.table_names
        else None
    )
    results, latency_ms = execute_schema_query(
        lambda: get_schema_browser().search(
            request.query,
            table_names=table_names,
            per_table_limit=request.per_table_limit,
            total_limit=request.total_limit,
        )
    )
    return {
        "query": request.query,
        "searched_tables": table_names or "ALL",
        "result_count": len(results),
        "latency_ms": latency_ms,
        "results": results,
    }


@app.get(
    "/products/",
    dependencies=[Depends(require_api_key)],
    tags=["product intelligence"],
)
def list_products(
    therapeutic_set: Literal["ANTIBACTERIAL", "ANTIFUNGAL"] | None = None,
) -> dict:
    results, latency_ms = execute_product_query(
        lambda: get_product_client().list_products(therapeutic_set)
    )
    return {"result_count": len(results), "latency_ms": latency_ms, "products": results}


@app.get(
    "/products/{product_key}/trials",
    dependencies=[Depends(require_api_key)],
    tags=["product intelligence"],
)
def product_trials(
    product_key: Annotated[str, Path(pattern=r"^[A-Za-z0-9_]+$", max_length=50)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    overall_status: Annotated[str | None, Query(max_length=100)] = None,
    phase: Annotated[str | None, Query(max_length=100)] = None,
) -> dict:
    key = product_key.upper()
    results, latency_ms = execute_product_query(
        lambda: get_product_client().product_trials(
            key,
            limit=limit,
            offset=offset,
            overall_status=overall_status,
            phase=phase,
        )
    )
    return {
        "product_key": key,
        "result_count": len(results),
        "limit": limit,
        "offset": offset,
        "latency_ms": latency_ms,
        "trials": results,
    }


@app.get(
    "/products/{product_key}/publications",
    dependencies=[Depends(require_api_key)],
    tags=["product intelligence"],
)
def product_publications(
    product_key: Annotated[str, Path(pattern=r"^[A-Za-z0-9_]+$", max_length=50)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> dict:
    key = product_key.upper()
    results, latency_ms = execute_product_query(
        lambda: get_product_client().product_publications(
            key, limit=limit, offset=offset
        )
    )
    return {
        "product_key": key,
        "result_count": len(results),
        "limit": limit,
        "offset": offset,
        "latency_ms": latency_ms,
        "publications": results,
    }


@app.get(
    "/trials/{nct_id}",
    dependencies=[Depends(require_api_key)],
    tags=["product intelligence"],
)
def get_trial(
    nct_id: Annotated[str, Path(pattern=r"^NCT[0-9]{8}$")],
) -> dict:
    results, latency_ms = execute_product_query(
        lambda: get_product_client().trial(nct_id)
    )
    if not results:
        raise HTTPException(status_code=404, detail="Trial not found")
    return {"nct_id": nct_id, "latency_ms": latency_ms, "records": results}


@app.get(
    "/publications/{pubmed_id}",
    dependencies=[Depends(require_api_key)],
    tags=["product intelligence"],
)
def get_publication(
    pubmed_id: Annotated[str, Path(pattern=r"^[0-9]+$", max_length=20)],
) -> dict:
    results, latency_ms = execute_product_query(
        lambda: get_product_client().publication(pubmed_id)
    )
    if not results:
        raise HTTPException(status_code=404, detail="Publication not found")
    return {"pubmed_id": pubmed_id, "latency_ms": latency_ms, "records": results}
