"""Read-only live smoke test for the structured product API client."""

from __future__ import annotations

import os
from pathlib import Path

from knowledge_search import SearchSettings
from product_intelligence import ProductIntelligenceClient


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def load_local_environment() -> None:
    env_path = WORKSPACE_ROOT / ".env"
    if env_path.exists():
        for raw in env_path.read_bytes().splitlines():
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"'))
    os.environ.setdefault(
        "SNOWFLAKE_PRIVATE_KEY_PATH",
        str(WORKSPACE_ROOT / "private_key.pem"),
    )


def main() -> None:
    load_local_environment()
    client = ProductIntelligenceClient(SearchSettings.from_environment())
    products, _ = client.list_products()
    trials, _ = client.product_trials("CRESEMBA", limit=1, offset=0)
    publications, _ = client.product_publications("CRESEMBA", limit=1, offset=0)
    print(
        {
            "products": len(products),
            "cresemba_trial_rows_returned": len(trials),
            "cresemba_publication_rows_returned": len(publications),
        }
    )


if __name__ == "__main__":
    main()
