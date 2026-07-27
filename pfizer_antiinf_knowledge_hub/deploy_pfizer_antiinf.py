from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
CREDENTIAL_ROOT = Path(
    os.getenv(
        "KNOWLEDGE_HUB_CREDENTIAL_ROOT",
        r"C:\Users\a287484\OneDrive - Syneos Health\Desktop\Desktop\RAG",
    )
)

DATABASE = "COMMUNICATIONS__EU__DER__DEV"
SCHEMA = "PFIZER_ANTIINF"
WAREHOUSE = "WH_COMMUNICATIONS__EU__DER"
SOURCE_STAGE = "PFIZER_ANTIINF_STREAMLIT_STAGE"
STREAMLIT_NAME = "PFIZER_ANTIINF"
APP_FILE = PROJECT_ROOT / "knowledge_hub_app.py"
ENV_FILE = PROJECT_ROOT / "environment.yml"

STAGED_PATHS = [
    "knowledge_hub_app.py",
    "knowledge_hub_service.py",
    "knowledge_hub_chunking.py",
    "environment.yml",
    "DESIGN.md",
    "README.md",
]


def load_env() -> None:
    env_path = CREDENTIAL_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_bytes().split(b"\n"):
        line = raw.rstrip(b"\r").decode("utf-8", errors="ignore").strip()
        if "=" not in line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"')
        if key and not os.environ.get(key):
            os.environ[key] = value


def connect():
    load_env()
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        load_pem_private_key,
    )
    import snowflake.connector as sf

    pem_path = CREDENTIAL_ROOT / "private_key.pem"
    if not pem_path.exists():
        raise FileNotFoundError(f"Missing Snowflake private key: {pem_path}")

    passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "").encode() or None
    key = load_pem_private_key(
        pem_path.read_bytes(),
        password=passphrase,
        backend=default_backend(),
    )
    private_key = key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    return sf.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        private_key=private_key,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", WAREHOUSE),
        database=os.getenv("SNOWFLAKE_DATABASE", DATABASE),
        schema=SCHEMA,
    )


def execute(cur, sql: str, label: str) -> None:
    print(f"  -> {label}")
    cur.execute(sql)
    try:
        cur.fetchall()
    except Exception:
        pass


def stage_file(cur, path: Path) -> None:
    execute(
        cur,
        f"PUT 'file://{path.as_posix()}' @{SOURCE_STAGE} OVERWRITE = TRUE AUTO_COMPRESS = FALSE",
        f"PUT {path.name}",
    )


def main() -> None:
    for path in (APP_FILE, ENV_FILE):
        if not path.exists():
            print(f"[error] missing {path}", file=sys.stderr)
            sys.exit(1)

    print(f"Deploying {STREAMLIT_NAME} from {PROJECT_ROOT}")
    connection = connect()
    cur = connection.cursor()
    try:
        execute(cur, f"USE WAREHOUSE {WAREHOUSE}", "USE warehouse")
        execute(cur, f"USE DATABASE {DATABASE}", "USE database")
        execute(cur, f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}", "CREATE schema")
        execute(cur, f"USE SCHEMA {SCHEMA}", "USE schema")
        execute(
            cur,
            f"""
            CREATE STAGE IF NOT EXISTS {SOURCE_STAGE}
                DIRECTORY = (ENABLE = TRUE)
                ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
                COMMENT = 'Application source files for PFIZER ANTIINF.'
            """,
            "CREATE source stage",
        )
        for relative in STAGED_PATHS:
            path = PROJECT_ROOT / relative
            if path.exists():
                stage_file(cur, path)
        execute(
            cur,
            f"""
            CREATE OR REPLACE STREAMLIT {STREAMLIT_NAME}
                ROOT_LOCATION = '@{DATABASE}.{SCHEMA}.{SOURCE_STAGE}'
                MAIN_FILE = '{APP_FILE.name}'
                QUERY_WAREHOUSE = {WAREHOUSE}
                COMMENT = 'Independent governed PFIZER ANTIINF Cortex Knowledge Hub.'
            """,
            "CREATE OR REPLACE STREAMLIT",
        )
        execute(cur, f"SHOW STREAMLITS LIKE '{STREAMLIT_NAME}'", "SHOW Streamlit")
        connection.commit()
    finally:
        cur.close()
        connection.close()

    print()
    print("PFIZER_ANTIINF deployed. Open Snowsight > Apps > Streamlit > PFIZER_ANTIINF.")


if __name__ == "__main__":
    main()
