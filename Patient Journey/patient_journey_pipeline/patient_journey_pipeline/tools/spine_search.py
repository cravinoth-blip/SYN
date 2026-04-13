"""
Tool: Evidence Spine Search — semantic retrieval across the local vector store.

Uses ChromaDB locally. For production, swap to Pinecone/Weaviate/OpenAI vector stores.

Supported ingestion formats: .txt, .md
"""

import hashlib
import time
from typing import Optional

import config
from tools.base import BaseTool

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_chunk_id(source: str, chunk_number: int, text: str) -> str:
    """Deterministic chunk ID based on source path, position, and content."""
    digest = hashlib.sha1(
        f"{source}|{chunk_number}|{text}".encode("utf-8")
    ).hexdigest()[:16]
    return f"chunk_{digest}"


# ─── Tool ────────────────────────────────────────────────────────────────────

class SpineSearchTool(BaseTool):
    name = "search_evidence_spine"
    description = (
        "Semantic search across the evidence spine vector store. "
        "Use this to find claims, patient quotes, clinical data, and published "
        "evidence relevant to a specific aspect of the patient journey."
    )

    def __init__(self):
        self._client = None
        self._collection = None
        self._openai = None

    def _get_collection(self):
        if self._collection is None:
            if chromadb is None:
                raise ImportError("chromadb not installed. pip install chromadb")
            self._client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
            self._collection = self._client.get_or_create_collection(
                name=config.SPINE_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _embed(self, text: str) -> list[float]:
        if OpenAI is None:
            raise ImportError("openai not installed. pip install openai")
        if self._openai is None:
            self._openai = OpenAI(api_key=config.OPENAI_API_KEY)

        last_error = None
        for attempt in range(3):
            try:
                resp = self._openai.embeddings.create(
                    model=config.EMBEDDING_MODEL,
                    input=text,
                )
                return resp.data[0].embedding
            except Exception as e:
                last_error = e
                time.sleep(2 ** attempt)

        raise RuntimeError(f"Embedding failed after 3 attempts: {last_error}")

    def _execute(self, query: str, top_k: Optional[int] = None) -> dict:
        top_k = top_k or config.TOP_K_RESULTS
        collection = self._get_collection()

        if collection.count() == 0:
            return {
                "result": [],
                "summary": "Evidence spine is empty. Ingest documents first.",
                "sources": [],
            }

        embedding = self._embed(query)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        docs  = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        passages = []
        for doc, meta, dist in zip(docs, metas, dists):
            passages.append({
                "text": doc,
                "metadata": meta or {},
                "similarity_estimate": round(max(0.0, 1 - dist), 3),
            })

        top_score = passages[0]["similarity_estimate"] if passages else "N/A"
        return {
            "result": passages,
            "summary": f"{len(passages)} passages returned, top similarity {top_score}",
            "sources": [
                {"title": p["metadata"].get("source", "spine"), "url": ""}
                for p in passages
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
                        "query": {
                            "type": "string",
                            "description": "Semantic search query to find relevant evidence passages",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of passages to return (default 15)",
                        },
                    },
                    "required": ["query"],
                },
            },
        }


# ─── Spine Ingestion Utility ─────────────────────────────────────────────────

def ingest_spine(file_paths: list[str], chunk_size: int = None, chunk_overlap: int = None):
    """
    Load documents into the evidence spine vector store.
    Currently supports .txt and .md files.

    Usage:
        from tools.spine_search import ingest_spine
        ingest_spine(["./data/spine_doc1.txt", "./data/notes.md"])
    """
    chunk_size    = chunk_size    or config.CHUNK_SIZE
    chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    step = chunk_size - chunk_overlap

    # ── Read files ────────────────────────────────────────────────
    texts = []
    for path in file_paths:
        if path.endswith(".txt") or path.endswith(".md"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    texts.append({"text": f.read(), "source": path})
            except Exception as e:
                print(f"  ⚠ Could not read {path}: {e}")
        else:
            print(f"  ⚠ Skipping unsupported file type: {path}")

    if not texts:
        raise ValueError("No supported documents were loaded for ingestion.")

    # ── Chunk (sliding window, per-document numbering) ────────────
    chunks = []
    for doc in texts:
        words = doc["text"].split()
        chunk_number = 0
        for i in range(0, len(words), step):
            chunk_words = words[i : i + chunk_size]
            if len(chunk_words) > 20:
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "id":           _make_chunk_id(doc["source"], chunk_number, chunk_text),
                    "text":         chunk_text,
                    "source":       doc["source"],
                    "chunk_number": chunk_number,
                })
                chunk_number += 1

    if not chunks:
        raise ValueError(
            "No chunks were generated. Check file content and chunking settings."
        )

    # ── Embed and store ───────────────────────────────────────────
    tool       = SpineSearchTool()
    collection = tool._get_collection()

    print(f"Ingesting {len(chunks)} chunks from {len(texts)} file(s)...")
    batch_size = 50

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        try:
            embeddings = [tool._embed(c["text"]) for c in batch]
            collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                embeddings=embeddings,
                metadatas=[
                    {"source": c["source"], "chunk_number": c["chunk_number"]}
                    for c in batch
                ],
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed ingesting batch starting at index {i}: {e}"
            ) from e

    print(f"Done. Collection now has {collection.count()} chunks.")
