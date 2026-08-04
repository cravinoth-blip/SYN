"""Read-only live smoke test for PFIZER_ANTIINF schema-wide browsing."""

from __future__ import annotations

from knowledge_search import SearchSettings
from schema_browser import SchemaBrowserClient
from smoke_product_intelligence import load_local_environment


def main() -> None:
    load_local_environment()
    client = SchemaBrowserClient(SearchSettings.from_environment())
    objects, _ = client.objects()
    rows, _ = client.rows(
        "KNOWLEDGE_COLLECTIONS", limit=1, offset=0, search=None
    )
    matches, _ = client.search(
        "Cresemba", table_names=None, per_table_limit=1, total_limit=20
    )
    print(
        {
            "schema_objects": len(objects),
            "knowledge_collection_rows_returned": len(rows),
            "tables_with_cresemba_matches": sorted(
                {match["TABLE_NAME"] for match in matches}
            ),
        }
    )


if __name__ == "__main__":
    main()
