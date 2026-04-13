"""
Ingest documents into the evidence spine vector store.

Usage:
    python ingest_spine.py ./data/spine_docs/*.pdf ./data/spine_docs/*.md
    python ingest_spine.py --help

This chunks the documents, generates embeddings, and stores them
in ChromaDB for semantic retrieval by the pipeline.
"""

import os
import sys
import glob
import argparse

from tools.spine_search import ingest_spine

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}


def resolve_files(inputs: list[str]) -> list[str]:
    file_paths = []

    for arg in inputs:
        expanded = glob.glob(arg)
        candidates = expanded if expanded else [arg]

        for path in candidates:
            if os.path.isfile(path):
                file_paths.append(os.path.abspath(path))
            else:
                print(f"  ⚠ Skipping: {path} (not found)")

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for path in file_paths:
        if path not in seen:
            seen.add(path)
            deduped.append(path)

    # Filter to supported file types
    valid: list[str] = []
    for path in deduped:
        ext = os.path.splitext(path)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            valid.append(path)
        else:
            print(f"  ⚠ Skipping unsupported file type: {path}")

    return valid


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into the evidence spine vector store."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Files or glob patterns to ingest (supported: .pdf, .md, .txt, .docx)",
    )
    args = parser.parse_args()

    file_paths = resolve_files(args.files)

    if not file_paths:
        print("No valid files found to ingest.")
        sys.exit(1)

    print(f"\nIngesting {len(file_paths)} files into evidence spine:\n")
    for f in file_paths:
        print(f"  • {f}")
    print()

    try:
        ingest_spine(file_paths)
    except Exception as e:
        print(f"\n✗ Spine ingestion failed: {type(e).__name__}: {e}\n")
        sys.exit(2)

    print("\n✓ Spine ingestion complete.\n")


if __name__ == "__main__":
    main()
