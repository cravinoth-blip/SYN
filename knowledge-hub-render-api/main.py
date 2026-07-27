"""Render-hosted API for the Snowflake Knowledge Hub Cortex Search service."""

from __future__ import annotations

import hmac
import os
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from knowledge_search import ConfigurationError, KnowledgeSearchClient, SearchSettings
from research_search import ResearchSearchClient


app = FastAPI(
    title="Knowledge Hub Search API",
    version="1.0.0",
    description=(
        "Secure API for COMMUNICATIONS__EU__DER__DEV.KNOWLEDGE_HUB."
        "KNOWLEDGE_SEARCH."
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


class ResearchQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["pubmed", "clinical_trials"]
    query_text: str = Field(min_length=1, max_length=1_000)
    top_k: int = Field(default=5, ge=1, le=10)


@lru_cache(maxsize=1)
def get_client() -> KnowledgeSearchClient:
    return KnowledgeSearchClient(SearchSettings.from_environment())


@lru_cache(maxsize=1)
def get_research_client() -> ResearchSearchClient:
    return ResearchSearchClient(SearchSettings.from_environment())


def require_api_key(
    supplied_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    expected_key = os.getenv("KNOWLEDGE_HUB_API_KEY", "")
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="KNOWLEDGE_HUB_API_KEY is not configured",
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
def metadata() -> dict[str, str]:
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


@app.post(
    "/research/query/",
    dependencies=[Depends(require_api_key)],
    tags=["research"],
)
def research_query(request: ResearchQueryRequest) -> dict:
    try:
        results, latency_ms = get_research_client().search(
            source=request.source,
            query=request.query_text,
            limit=request.top_k,
        )
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Research search failed: {type(exc).__name__}",
        ) from exc
    return {
        "source": request.source,
        "query": request.query_text,
        "result_count": len(results),
        "latency_ms": latency_ms,
        "context": results,
    }
