"""
Tool: Snowflake Evidence Search

Queries COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS (and any other configured
tables) using keyword search. Called by the model during pipeline passes to
retrieve real evidence from the Snowflake knowledge base.

Credentials are read from environment variables set by the FastAPI backend's
load_dotenv() call, so no extra .env wiring is needed here.
"""

import os
from typing import Optional

import config
from tools.base import BaseTool

try:
    import snowflake.connector
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key, Encoding, PrivateFormat, NoEncryption,
    )
    _snowflake_available = True
except ImportError:
    _snowflake_available = False


# ---------------------------------------------------------------------------
# Fully-qualified table registry
# Add more entries here as new tables become available.
# ---------------------------------------------------------------------------
SNOWFLAKE_TABLE_REGISTRY = {
    "PUBLICATIONS": {
        "fq_name": "COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS",
        "text_cols": ["ABSTRACT", "TITLE"],
        "meta_cols": ["PMID", "TITLE", "JOURNAL", "PUBLICATION_DATE"],
    },
    "COMPILE_ADD_ON": {
        "fq_name": "COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS",
        "text_cols": ["ABSTRACT", "TITLE"],
        "meta_cols": ["PMID", "TITLE", "JOURNAL", "PUBLICATION_DATE"],
    },
    "PUBMED_DETAILS": {
        "fq_name": "COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS",
        "text_cols": ["ABSTRACT", "TITLE"],
        "meta_cols": ["PMID", "TITLE", "JOURNAL", "PUBLICATION_DATE"],
    },
}

# Default tables to search when the model doesn't specify
DEFAULT_TABLES = ["PUBLICATIONS"]


class SnowflakeSearchTool(BaseTool):
    name = "search_snowflake_evidence"
    description = (
        "Search the Snowflake evidence database for published clinical evidence, "
        "PubMed abstracts, and disease-specific research. "
        "Queries COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS. "
        "Use this to find real clinical data, trial results, and epidemiology "
        "that support specific patient journey claims."
    )

    def __init__(self):
        self._conn = None
        self._col_cache: dict[str, list[str]] = {}

    def _get_private_key(self) -> bytes:
        import base64 as _b64
        key_val = os.getenv("SNOWFLAKE_PRIVATE_KEY", "").strip()
        if not key_val:
            raise ValueError("SNOWFLAKE_PRIVATE_KEY env var not set")
        pem = _b64.b64decode(key_val) if not key_val.startswith("-----") else key_val.replace("\\n", "\n").encode()
        passphrase_str = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")
        passphrase = passphrase_str.encode() if passphrase_str else None
        private_key = load_pem_private_key(pem, password=passphrase)
        return private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())

    def _connect(self):
        account   = os.getenv("SNOWFLAKE_ACCOUNT", "")
        user      = os.getenv("SNOWFLAKE_USER", "")
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "")
        database  = os.getenv("SNOWFLAKE_DATABASE", "")
        schema    = os.getenv("SNOWFLAKE_SCHEMA", "")

        if not account:
            raise RuntimeError("Snowflake credentials not configured (SNOWFLAKE_ACCOUNT missing)")

        return snowflake.connector.connect(
            account=account,
            user=user,
            private_key=self._get_private_key(),
            warehouse=warehouse,
            database=database,
            schema=schema,
        )

    def _discover_columns(self, cur, fq_name: str) -> list[str]:
        if fq_name in self._col_cache:
            return self._col_cache[fq_name]
        try:
            cur.execute(f"DESCRIBE TABLE {fq_name}")
            cols = [row[0].upper() for row in cur.fetchall()]
            self._col_cache[fq_name] = cols
            return cols
        except Exception as e:
            print(f"    Could not describe {fq_name}: {e}")
            return []

    def _execute(
        self,
        query: str,
        tables: Optional[list] = None,
        top_k: Optional[int] = None,
    ) -> dict:
        if not _snowflake_available:
            return {
                "result": [],
                "summary": "snowflake-connector-python not installed.",
                "sources": [],
            }

        tables = tables or DEFAULT_TABLES
        top_k  = top_k or config.TOP_K_RESULTS

        # Extract keywords from query (words > 3 chars)
        keywords = [w.strip(".,;:()") for w in query.split() if len(w.strip(".,;:()")) > 3]
        if not keywords:
            keywords = [query]

        passages = []
        seen_fq  = set()

        try:
            conn = self._connect()
            cur  = conn.cursor()

            for table_key in tables:
                cfg = SNOWFLAKE_TABLE_REGISTRY.get(str(table_key).upper())
                if not cfg:
                    print(f"    Unknown table key '{table_key}', skipping.")
                    continue

                fq_name = cfg["fq_name"]
                if fq_name in seen_fq:
                    continue
                seen_fq.add(fq_name)

                actual_cols = self._discover_columns(cur, fq_name)
                if not actual_cols:
                    continue

                text_cols = [c for c in cfg["text_cols"] if c in actual_cols]
                meta_cols = [c for c in cfg["meta_cols"] if c in actual_cols]

                if not text_cols:
                    print(f"    No searchable text columns in {fq_name} "
                          f"(tried {cfg['text_cols']}; available: {actual_cols[:8]})")
                    continue

                # Build ILIKE filter
                like_clauses = " OR ".join(
                    f"UPPER({col}) LIKE '%{kw.upper()}%'"
                    for col in text_cols
                    for kw in keywords
                )

                select_cols = ", ".join(text_cols + meta_cols)
                sql = (
                    f"SELECT {select_cols} "
                    f"FROM {fq_name} "
                    f"WHERE {like_clauses} "
                    f"LIMIT {top_k * 2}"
                )

                try:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    col_names = [d[0].upper() for d in cur.description]
                except Exception as e:
                    print(f"    Query error on {fq_name}: {e}")
                    continue

                for row in rows:
                    rec  = dict(zip(col_names, row))
                    text = " | ".join(str(rec[c]) for c in text_cols if rec.get(c))
                    src  = str(rec.get("TITLE", rec.get(col_names[0], fq_name)))[:120]
                    pmid = rec.get("PMID", "")
                    passages.append({
                        "text": text,
                        "source": src,
                        "pmid": str(pmid) if pmid else "",
                        "table": fq_name,
                    })

            cur.close()
            conn.close()

        except Exception as exc:
            return {
                "result": [],
                "summary": f"Snowflake connection error: {exc}",
                "sources": [],
            }

        passages = passages[:top_k]
        top_src = passages[0]["source"] if passages else "N/A"

        return {
            "result": passages,
            "summary": (
                f"{len(passages)} evidence passages from Snowflake "
                f"(tables: {list(seen_fq)}). Top source: {top_src}"
            ),
            "sources": [
                {
                    "title": p["source"],
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" if p.get("pmid") else "",
                }
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
                            "description": (
                                "Natural language search query. Be specific: include "
                                "disease name, mechanism, phase of journey, or clinical concept."
                            ),
                        },
                        "tables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Tables to search. Options: 'PUBLICATIONS', 'COMPILE_ADD_ON', "
                                "'PUBMED_DETAILS'. Defaults to ['PUBLICATIONS']."
                            ),
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Max passages to return (default 15).",
                        },
                    },
                    "required": ["query"],
                },
            },
        }
