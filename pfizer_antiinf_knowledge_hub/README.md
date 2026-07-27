# PFIZER ANTIINF Knowledge Hub

Fully isolated Snowflake-native knowledge application.

## Objects

- Database: `COMMUNICATIONS__EU__DER__DEV`
- Schema: `PFIZER_ANTIINF`
- Streamlit app: `PFIZER_ANTIINF`
- Source-file stage: `PFIZER_ANTIINF.KNOWLEDGE_FILES`
- Streamlit stage: `PFIZER_ANTIINF.PFIZER_ANTIINF_STREAMLIT_STAGE`
- Cortex Search service: `PFIZER_ANTIINF.KNOWLEDGE_SEARCH`

Tables, stages, application permissions, audit events, ingestion jobs, chunks,
and search data exist only in `PFIZER_ANTIINF`. The runtime schema constant is
hard-coded and cannot be redirected to `KNOWLEDGE_HUB`.

## Setup and deployment

```powershell
python run_snowflake_sql.py pfizer_antiinf_knowledge_hub/setup_pfizer_antiinf_core.sql
python run_snowflake_sql.py pfizer_antiinf_knowledge_hub/setup_pfizer_antiinf_search.sql
python pfizer_antiinf_knowledge_hub/deploy_pfizer_antiinf.py
```
