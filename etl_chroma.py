"""
Local ETL Pipeline - ChromaDB version.
Extracts text from documents, chunks, generates OpenAI embeddings,
and stores everything in a local persistent ChromaDB collection.
"""

import os, json, re, logging
from pathlib import Path

import os
import chromadb
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from tqdm import tqdm

# Reuse all extraction/chunking/metadata helpers from etl_local
import etl_local as etl

# ============================================================
# CONFIGURATION
# ============================================================
CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "rag_docs"
INPUT_FOLDER = etl.INPUT_FOLDER

# ============================================================
# CHROMADB SETUP
# ============================================================
def get_collection(openai_api_key: str):
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    ef = OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-3-small",
    )
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return collection

# ============================================================
# ETL
# ============================================================
def run_etl(collection, openai_client):
    files = [f for f in INPUT_FOLDER.iterdir() if f.is_file()]
    print(f"Found {len(files)} files to process")

    existing_ids = set(collection.get(include=[])["ids"])
    print(f"Existing chunks in DB: {len(existing_ids)}")

    skipped = 0
    added = 0

    for file_path in tqdm(files, desc="Processing files"):
        document = etl.extract_file(file_path)
        if not document or not document.get("text_data"):
            continue

        # DOI + Crossref metadata (PDFs only)
        doi, meta_crossref = None, {}
        if file_path.suffix.lower() == ".pdf":
            doi = etl.extract_doi_from_pdf(file_path)
            if doi:
                meta_crossref = etl.fetch_crossref_metadata(doi)

        full_text = document.get("full_text", "") or "\n".join(
            d["text"] for d in document["text_data"]
        )
        ai_title = etl.extract_title_from_text(openai_client, full_text)
        final_title = meta_crossref.get("title") or ai_title or document.get("title", "Untitled")
        summary = etl.generate_summary(openai_client, full_text)

        for page_data in document["text_data"]:
            text = page_data.get("text", "").strip()
            if not text:
                continue

            chunks = etl.chunk_text(text)
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                chunk_id = f"{file_path.name}--p{page_data.get('page_number', 1)}--c{i}"

                if chunk_id in existing_ids:
                    skipped += 1
                    continue

                metadata = {
                    "source_file": file_path.name,
                    "chunk_index": i,
                    "page_reference": f"p. {page_data.get('page_number', 1)}",
                    "is_table": str(page_data.get("is_table", False)),
                    "file_type": file_path.suffix.replace(".", "").lower(),
                    "title": final_title[:500] if final_title else "",
                    "authors": (meta_crossref.get("authors") or "")[:500],
                    "published": (meta_crossref.get("published") or ""),
                    "doi": (meta_crossref.get("doi") or doi or ""),
                    "citation": (meta_crossref.get("Citation") or "")[:1000],
                    "citation_count": meta_crossref.get("citation_count", 0),
                    "summary": summary[:1000] if summary else "",
                }

                # ChromaDB requires string/int/float/bool metadata values
                metadata = {k: (v if v is not None else "") for k, v in metadata.items()}

                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[metadata],
                )
                existing_ids.add(chunk_id)
                added += 1

    print(f"\nDone. Added {added} new chunks, skipped {skipped} existing.")
    print(f"Total chunks in DB: {collection.count()}")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("RAG ETL Pipeline - ChromaDB")
    print("=" * 60)
    print(f"Input:  {INPUT_FOLDER}")
    print(f"DB:     {CHROMA_PATH}")
    print()

    openai_client = etl.get_openai_client()
    if openai_client is None:
        print("Cannot proceed without OpenAI")
        raise SystemExit(1)

    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    collection = get_collection(openai_api_key)
    print(f"Collection '{COLLECTION_NAME}' ready. Current count: {collection.count()}")
    print()

    run_etl(collection, openai_client)
    print("\nPipeline complete!")
