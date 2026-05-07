from __future__ import annotations

import hashlib
import math
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import get_settings
from app.models import DocumentChunk, ParsedDocument, ProjectFile

try:
    import chromadb
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent
    chromadb = None


settings = get_settings()
REPO_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: str
    file_id: str
    filename: str
    chunk_index: int
    text: str
    score: float
    distance: float | None
    metadata: dict[str, Any]


class UploadEmbeddingFunction:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    @property
    def provider(self) -> str:
        return "openai" if settings.openai_api_key else "local_hash"

    @property
    def model_name(self) -> str:
        return settings.openai_embedding_model if settings.openai_api_key else "local_hash_1536"

    def name(self) -> str:
        return f"{self.provider}:{self.model_name}"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embed(input)

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self.embed(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self.embed(input)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if settings.openai_api_key:
            if self._client is None:
                self._client = OpenAI(api_key=settings.openai_api_key)
            response = self._client.embeddings.create(
                model=settings.openai_embedding_model,
                input=texts,
            )
            return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        return [_hash_embedding(text, dimensions=settings.vector_embedding_dimensions) for text in texts]


embedding_function = UploadEmbeddingFunction()


def _vector_db_path() -> Path:
    path = Path(settings.vector_db_path)
    return path if path.is_absolute() else REPO_ROOT / path


def _hash_embedding(text: str, *, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def vector_store_available() -> bool:
    return chromadb is not None


def _collection():
    if chromadb is None:
        raise RuntimeError("chromadb is not installed. Run `pip install -e \".[dev]\"` in apps/api.")
    path = _vector_db_path()
    path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(path))
    return client.get_or_create_collection(
        name=settings.vector_collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_function,
    )


def index_document_chunks(
    *,
    file: ProjectFile,
    parsed_document: ParsedDocument,
    chunks: list[DocumentChunk],
) -> dict[str, Any]:
    if not chunks:
        return {"status": "skipped", "reason": "no_chunks"}
    if chromadb is None:
        return {"status": "skipped", "reason": "chromadb_not_installed"}

    collection = _collection()
    project_id = str(file.project_id)
    file_id = str(file.file_id)
    parsed_document_id = str(parsed_document.parsed_document_id)
    ids = [str(chunk.chunk_id) for chunk in chunks]
    documents = [chunk.chunk_text for chunk in chunks]
    metadatas = [
        {
            "project_id": project_id,
            "file_id": file_id,
            "filename": file.filename,
            "file_type": file.file_type,
            "parsed_document_id": parsed_document_id,
            "chunk_id": str(chunk.chunk_id),
            "chunk_index": chunk.chunk_index,
            "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else "",
            "source": "internal_upload",
        }
        for chunk in chunks
    ]
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    reference = {
        "provider": "chroma",
        "path": str(_vector_db_path()),
        "collection": settings.vector_collection_name,
        "metric": "cosine",
        "embedding_provider": embedding_function.provider,
        "embedding_model": embedding_function.model_name,
    }
    for chunk in chunks:
        chunk.embedding_ref = reference
    return {"status": "indexed", "chunk_count": len(chunks), **reference}


def index_external_source_chunks(
    *,
    project_id: uuid.UUID | str,
    section_name: str,
    source_type: str,
    source_id: str,
    source_title: str,
    source_url: str | None,
    citation: str,
    chunks: list[str],
) -> dict[str, Any]:
    if not chunks:
        return {"status": "skipped", "reason": "no_chunks"}
    if chromadb is None:
        return {"status": "skipped", "reason": "chromadb_not_installed"}

    collection = _collection()
    ids = [
        _stable_chunk_id(
            project_id=str(project_id),
            section_name=section_name,
            source_type=source_type,
            source_id=source_id,
            chunk_index=index,
        )
        for index, _chunk in enumerate(chunks)
    ]
    metadatas = [
        {
            "project_id": str(project_id),
            "section_name": section_name,
            "source_type": source_type,
            "source_id": source_id,
            "source_title": source_title,
            "source_url": source_url or "",
            "citation": citation,
            "chunk_id": ids[index],
            "chunk_index": index,
            "source": "external_connector",
        }
        for index, _chunk in enumerate(chunks)
    ]
    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
    return {
        "status": "indexed",
        "chunk_count": len(chunks),
        "provider": "chroma",
        "path": str(_vector_db_path()),
        "collection": settings.vector_collection_name,
        "metric": "cosine",
        "embedding_provider": embedding_function.provider,
        "embedding_model": embedding_function.model_name,
    }


def delete_file_vectors(file_id: uuid.UUID) -> None:
    if chromadb is None:
        return
    try:
        collection = _collection()
        collection.delete(where={"file_id": str(file_id)})
    except Exception:
        return


def search_project_chunks(
    *,
    project_id: uuid.UUID,
    query: str,
    top_k: int = 8,
    excluded_document_ids: list[str] | None = None,
) -> list[VectorSearchResult]:
    if chromadb is None or not query.strip():
        return []

    try:
        collection = _collection()
    except Exception:
        return []
    requested = max(top_k + len(excluded_document_ids or []), top_k)
    try:
        results = collection.query(
            query_texts=[query],
            n_results=requested,
            where={"project_id": str(project_id)},
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []
    excluded = set(excluded_document_ids or [])
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    matches: list[VectorSearchResult] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        if metadata.get("file_id") in excluded:
            continue
        matches.append(
            VectorSearchResult(
                chunk_id=str(metadata.get("chunk_id", "")),
                file_id=str(metadata.get("file_id", "")),
                filename=str(metadata.get("filename", "upload")),
                chunk_index=int(metadata.get("chunk_index", 0)),
                text=document,
                score=round(max(0.0, 1.0 - float(distance)), 4) if distance is not None else 0.0,
                distance=float(distance) if distance is not None else None,
                metadata=dict(metadata),
            )
        )
        if len(matches) >= top_k:
            break
    return matches


def search_external_source_chunks(
    *,
    project_id: uuid.UUID | str,
    source_type: str,
    section_name: str,
    query: str,
    top_k: int,
) -> list[VectorSearchResult]:
    if chromadb is None or not query.strip():
        return []
    try:
        collection = _collection()
        results = collection.query(
            query_texts=[query],
            n_results=max(top_k * 4, top_k),
            where={"project_id": str(project_id)},
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    matches: list[VectorSearchResult] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        if metadata.get("source_type") != source_type:
            continue
        if metadata.get("section_name") != section_name:
            continue
        matches.append(
            VectorSearchResult(
                chunk_id=str(metadata.get("chunk_id", "")),
                file_id=str(metadata.get("source_id", "")),
                filename=str(metadata.get("source_title", source_type)),
                chunk_index=int(metadata.get("chunk_index", 0)),
                text=document,
                score=round(max(0.0, 1.0 - float(distance)), 4) if distance is not None else 0.0,
                distance=float(distance) if distance is not None else None,
                metadata=dict(metadata),
            )
        )
        if len(matches) >= top_k:
            break
    return matches


def _stable_chunk_id(
    *,
    project_id: str,
    section_name: str,
    source_type: str,
    source_id: str,
    chunk_index: int,
) -> str:
    raw = f"{project_id}:{section_name}:{source_type}:{source_id}:{chunk_index}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{source_type.lower()}-{digest[:32]}"
