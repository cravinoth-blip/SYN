"""
Configuration for the Patient Journey Pipeline.

Secrets (API keys, Snowflake credentials) are read from environment variables.
Runtime tuning constants are defined here and validated at import time.
"""

import os

# ─── Base directory (anchors all relative paths) ────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _require(name: str) -> str:
    """Return the value of a required environment variable, or raise on startup."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# ─── LLM Settings ────────────────────────────────────────────────────────────
OPENAI_API_KEY = _require("OPENAI_API_KEY")

_DEFAULT_MODEL    = _optional("DEFAULT_MODEL", "gpt-4o")
MODEL_GENERATION  = _optional("MODEL_GENERATION",  _DEFAULT_MODEL)  # Pass 1, 2
MODEL_ARTIFACTS   = _optional("MODEL_ARTIFACTS",   _DEFAULT_MODEL)  # Pass 3
MODEL_POLISH      = _optional("MODEL_POLISH",       _DEFAULT_MODEL)  # Pass 4

MAX_TOKENS_PER_PASS = int(_optional("MAX_TOKENS_PER_PASS", "16000"))
TEMPERATURE         = float(_optional("TEMPERATURE", "0.3"))

# ─── Snowflake ────────────────────────────────────────────────────────────────
SNOWFLAKE_ACCOUNT    = _optional("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER       = _optional("SNOWFLAKE_USER")
SNOWFLAKE_WAREHOUSE  = _optional("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE   = _optional("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA     = _optional("SNOWFLAKE_SCHEMA")
SNOWFLAKE_PRIVATE_KEY            = _optional("SNOWFLAKE_PRIVATE_KEY")
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE = _optional("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")

# ─── Tool API Keys ────────────────────────────────────────────────────────────
TAVILY_API_KEY = _optional("TAVILY_API_KEY")

# ClinicalTrials.gov and openFDA are free — no keys needed
CLINICAL_TRIALS_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
FDA_LABEL_BASE_URL       = "https://api.fda.gov/drug/label.json"

# ─── Vector Store (Evidence Spine) ───────────────────────────────────────────
CHROMA_PERSIST_DIR    = os.path.join(BASE_DIR, "data", "chroma_spine")
SPINE_COLLECTION_NAME = "evidence_spine"
EMBEDDING_MODEL       = "text-embedding-3-small"
CHUNK_SIZE            = 800   # approximate words per chunk (split by whitespace)
CHUNK_OVERLAP         = 100   # words of overlap between consecutive chunks
TOP_K_RESULTS         = 15    # passages returned per search

# ─── Output Paths ─────────────────────────────────────────────────────────────
OUTPUT_DIR    = os.path.join(BASE_DIR, "output")
AUDIT_LOG_DIR = os.path.join(OUTPUT_DIR, "audit")

# ─── Pipeline Behaviour ───────────────────────────────────────────────────────
MAX_TOOL_CALLS_PASS1 = 60   # safety cap on model tool calls per pass
MAX_TOOL_CALLS_PASS2 = 40
MAX_TOOL_CALLS_PASS3 = 30
PASS2_CONFIDENCE_THRESHOLD = "MEDIUM"

# ─── Startup validation ───────────────────────────────────────────────────────
if not (0.0 <= TEMPERATURE <= 2.0):
    raise ValueError(f"TEMPERATURE must be between 0 and 2, got {TEMPERATURE}")

if CHUNK_SIZE <= 0:
    raise ValueError(f"CHUNK_SIZE must be > 0, got {CHUNK_SIZE}")

if CHUNK_OVERLAP < 0 or CHUNK_OVERLAP >= CHUNK_SIZE:
    raise ValueError(
        f"CHUNK_OVERLAP must be >= 0 and < CHUNK_SIZE ({CHUNK_SIZE}), got {CHUNK_OVERLAP}"
    )

if TOP_K_RESULTS <= 0:
    raise ValueError(f"TOP_K_RESULTS must be > 0, got {TOP_K_RESULTS}")

if MAX_TOKENS_PER_PASS <= 0:
    raise ValueError(f"MAX_TOKENS_PER_PASS must be > 0, got {MAX_TOKENS_PER_PASS}")
