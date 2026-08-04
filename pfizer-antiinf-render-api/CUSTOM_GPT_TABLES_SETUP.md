# PFIZER ANTIINF Custom GPT table connector

This bundle connects a Custom GPT to fixed, read-only HTTPS endpoints backed by
the structured Snowflake tables in
`COMMUNICATIONS__EU__DER__DEV.PFIZER_ANTIINF`.

## 1. Deploy the API

Deploy `render.yaml` from the repository root. Configure these Render secrets:

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_ROLE=RL_COMMUNICATIONS_EU_DER`
- `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` when needed
- Secret file `private_key.pem` mounted at `/etc/secrets/private_key.pem`
- `PFIZER_ANTIINF_API_KEY` as a long random secret

Do not put the private key or API key in Git or in Custom GPT instructions.

Confirm that `https://<render-host>/health` returns `{"status":"ok"}`.

No new Snowflake role is created or required. The API uses the existing
`RL_COMMUNICATIONS_EU_DER` role for every Snowflake connection.

## 2. Configure the Custom GPT

1. Open the GPT editor and select **Configure**.
2. Paste `custom-gpt-tables-instructions.txt` into **Instructions**.
3. Under **Actions**, import `custom-gpt-tables-action.json`.
4. If necessary, replace `servers[0].url` with the deployed HTTPS hostname.
5. Set authentication to **API Key**.
6. Select **Custom** authentication and use header name `X-API-Key`.
7. Enter the same secret stored in Render as `PFIZER_ANTIINF_API_KEY`.
8. Test the schema inventory, schema search, table rows, semantic search, and
   product operations before publishing.

## 3. Suggested Action tests

- `listPfizerAntiinfSchemaObjects`
- `searchPfizerAntiinfSchema` with `query=Cresemba`
- `getPfizerAntiinfTableRows` with `table_name=KNOWLEDGE_COLLECTIONS`, `limit=3`
- `searchPfizerAntiinfKnowledge` with a question about anti-infective evidence
- `listAntiInfectiveProducts` with `therapeutic_set=ANTIFUNGAL`
- `getAntiInfectiveProductTrials` with `product_key=CRESEMBA`, `limit=3`
- `getAntiInfectiveProductPublications` with `product_key=ZAVICEFTA`, `limit=3`
- `getAntiInfectiveTrialByNctId` using an NCT ID returned by the trials action
- `getAntiInfectivePublicationByPmid` using a PMID returned by the publications action

## Included files

- `main.py`: authenticated FastAPI routes
- `product_intelligence.py`: fixed read-only Snowflake queries
- `schema_browser.py`: allowlisted discovery and retrieval across every table/view
- `knowledge_search.py`: existing Cortex Search client restricted to `PFIZER_ANTIINF`
- `custom-gpt-tables-action.json`: OpenAPI 3.1 Action definition
- `custom-gpt-tables-instructions.txt`: ready-to-paste GPT instructions
- `render.yaml`, `requirements.txt`, `.env.example`: deployment configuration
- `tests/test_api.py`: API tests
- `smoke_product_intelligence.py`: optional read-only live connection test
- `smoke_schema_browser.py`: optional all-table/view read-only smoke test

The API never accepts arbitrary SQL. A caller can select an object only when its
name is present in the live PFIZER_ANTIINF table/view inventory; other objects
are rejected.
