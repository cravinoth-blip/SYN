"""
Snowflake client — queries COMPILE_ADD_ON and PUBMED_DETAILS tables
using vector cosine similarity, mirroring the main RAG app.py pattern.
"""

import os
import base64
import json
from typing import Optional
from cryptography.hazmat.primitives.serialization import load_pem_private_key

import snowflake.connector
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "")
SNOWFLAKE_PRIVATE_KEY = os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")

# Table configs — fully-qualified names (DB.SCHEMA.TABLE) + column mappings.
# COMPILE_ADD_ON is the Snowflake database; PUBMED_DETAILS is the schema;
# PUBLICATIONS is the actual table. Use cross-database references.
TABLE_CONFIG = {
    "COMPILE_ADD_ON": {
        "fq_name": "COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS",
        "search_mode": "keyword",        # no embedding col — keyword search
        "text_cols": ["ABSTRACT", "TITLE"],
        "meta_cols": ["PMID", "TITLE", "JOURNAL", "PUBLICATION_DATE"],
    },
    "PUBMED_DETAILS": {
        "fq_name": "COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS",
        "search_mode": "keyword",
        "text_cols": ["ABSTRACT", "TITLE"],
        "meta_cols": ["PMID", "TITLE", "JOURNAL", "PUBLICATION_DATE"],
    },
    "PUBLICATIONS": {
        "fq_name": "COMPILE_ADD_ON.PUBMED_DETAILS.PUBLICATIONS",
        "search_mode": "keyword",
        "text_cols": ["ABSTRACT", "TITLE"],
        "meta_cols": ["PMID", "TITLE", "JOURNAL", "PUBLICATION_DATE"],
    },
}


def _get_private_key():
    """Load private key from env var (base64-encoded PEM or raw PEM with \\n escapes)."""
    import base64 as _b64
    key_val = SNOWFLAKE_PRIVATE_KEY.strip()
    if key_val.startswith("-----"):
        pem = key_val.replace("\\n", "\n").encode()
    else:
        pem = _b64.b64decode(key_val)
    passphrase = SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.encode() if SNOWFLAKE_PRIVATE_KEY_PASSPHRASE else None
    private_key = load_pem_private_key(pem, password=passphrase)
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
    return private_key.private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )


def _embed(text: str) -> list[float]:
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


def _get_connection():
    """Open a Snowflake connection using private-key auth."""
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        private_key=_get_private_key(),
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
    )


def _discover_columns(cur, fq_table: str) -> list[str]:
    """Return lowercase column names for a fully-qualified table."""
    try:
        cur.execute(f"DESCRIBE TABLE {fq_table}")
        return [row[0].upper() for row in cur.fetchall()]
    except Exception:
        return []


def query_snowflake_tables(
    disease: str,
    tables: list[str],
    top_k: int = 20,
) -> list[dict]:
    """
    Query Snowflake tables for disease-relevant evidence.
    Uses keyword search (ILIKE) on TITLE + ABSTRACT columns.
    Tables may be short aliases (COMPILE_ADD_ON) or fully-qualified names.
    Returns a flat list of passage dicts.
    """
    if not SNOWFLAKE_ACCOUNT:
        print("WARNING: Snowflake credentials not configured — skipping DB query.")
        return []

    # Build keyword fragments from the disease name
    keywords = [w for w in disease.split() if len(w) > 3]
    if not keywords:
        keywords = [disease]

    passages = []
    seen_fq = set()   # avoid querying the same physical table twice

    try:
        private_key_der = _get_private_key()
        conn = snowflake.connector.connect(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            private_key=private_key_der,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
        )
        cur = conn.cursor()

        for table in tables:
            cfg = TABLE_CONFIG.get(table.upper())
            if not cfg:
                print(f"WARNING: No config for table '{table}', skipping.")
                continue

            fq_name = cfg["fq_name"]
            if fq_name in seen_fq:
                continue
            seen_fq.add(fq_name)

            # Discover actual columns to avoid missing-column errors
            actual_cols = _discover_columns(cur, fq_name)
            if not actual_cols:
                print(f"WARNING: Could not describe {fq_name}, skipping.")
                continue

            # Identify which text and meta columns exist
            text_cols   = [c for c in cfg["text_cols"] if c in actual_cols]
            meta_cols   = [c for c in cfg["meta_cols"] if c in actual_cols]

            if not text_cols:
                # Fall back: use first non-ID string column
                print(f"WARNING: None of {cfg['text_cols']} found in {fq_name}. "
                      f"Available: {actual_cols[:10]}")
                continue

            # Build ILIKE filter across all text columns
            like_clauses = " OR ".join(
                f"UPPER({col}) LIKE '%{kw.upper()}%'"
                for col in text_cols
                for kw in keywords
            )

            select_cols = ", ".join(text_cols + meta_cols)
            sql = f"""
                SELECT {select_cols}
                FROM {fq_name}
                WHERE {like_clauses}
                LIMIT {top_k * 2}
            """
            try:
                cur.execute(sql)
                rows = cur.fetchall()
                col_names = [desc[0].upper() for desc in cur.description]
            except Exception as e:
                print(f"Query failed for {fq_name}: {e}")
                continue

            for row in rows:
                record = dict(zip(col_names, row))
                # Concatenate available text columns into a single passage
                text = " | ".join(
                    str(record.get(c, "")) for c in text_cols if record.get(c)
                )
                title = record.get("TITLE", record.get(col_names[0], fq_name))
                passages.append({
                    "text": text,
                    "source": str(title)[:120],
                    "table": fq_name,
                    "score": 1.0,   # keyword match — no similarity score
                })

        cur.close()
        conn.close()

    except Exception as exc:
        print(f"Snowflake query error: {exc}")

    return passages[:top_k]
