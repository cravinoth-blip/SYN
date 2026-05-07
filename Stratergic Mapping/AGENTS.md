# AGENTS.md

Guidance for AI agents and coding assistants working in this repository.

## Active Repository Context

Use this `Stratergic Mapping` repository as the only active workspace for this project.

- Ignore the sibling `RAG` root unless the user explicitly asks to work there.
- Run reads, writes, commands, tests, builds, and repo-status checks from this repository.
- Do not create or update agent guidance files in `RAG` for Stratergic Mapping work.
- If a session starts from another working directory, switch context to this repository before acting.

## Project

This repo implements the Stratergic Mapping / 7Cs Disease Intelligence Platform.

The intended product workflow is:

Intake -> Uploads -> Parsing -> Retrieval Planning -> Evidence Retrieval -> Evidence Normalization/Scoring -> Generation/Regeneration -> Validation Hard Gate -> Version Publish -> Workspace -> Export

The application is a portable Docker app with:

- `apps/web`: Next.js frontend
- `apps/api`: FastAPI backend
- `apps/worker`: async worker scaffold
- `packages/shared`: shared constants/types
- `infra/docker`: deployment support
- `docs`: architecture and implementation notes

## Non-Negotiable Product Rules

- Generate all seven sections: Condition, Compound, Context, Company, Customer, Channel, Competition.
- Block generation when required intake fields are incomplete.
- Supporting uploads must be PDF or PPTX only. Do not add DOCX upload support unless the product design changes.
- Draft generated report content must not be shown in the workspace.
- Workspace and export must read only from published versions.
- Only `VALIDATED_READY` candidates can be published.
- Published versions are immutable.
- Latest published version should open first, with version history available.
- Regeneration must create a new candidate version.
- Section regeneration should copy untouched sections forward from the parent version after validation passes.
- Authentication is intentionally omitted for now, but code should keep a future auth/access boundary in mind.

## Architecture Expectations

Backend service boundaries should remain clear:

- Project service
- Upload service
- Document parsing service
- Retrieval planner
- Source connector service
- Evidence normalization and scoring
- LLM router
- Prompt assembly
- Generation service
- Regeneration service
- Validation and assurance
- Version publishing
- Citation/reference handling
- Workspace read model
- Export service
- Audit/activity logging

Prefer extending these boundaries over creating unrelated parallel paths.

## Data Model

The PostgreSQL model should follow the supplied ERD:

- `project`
- `project_file`
- `parsed_document`
- `document_chunk`
- `candidate_version`
- `validation_report`
- `validation_finding`
- `evidence_item`
- `version`
- `section_output`
- `citation`
- `export_job`
- `audit_log`

Use JSON/JSONB-style fields for flexible metadata, exclusions, structured fields, and raw payloads.

## Evidence Rules

The required evidence source families are:

- Internal uploads
- PubMed / PMC
- ClinicalTrials
- Guidelines
- Regulatory
- HTA
- Epidemiology
- Congress
- News
- Advocacy

All source data should be normalized into `evidence_item` records before generation uses it. Prompts should cite only normalized evidence.

Evidence classification labels:

- `FactBacked`
- `AIInference`
- `ClientInternalInput`

## Validation Gate

Validation is a hard gate. Do not bypass it for convenience.

Validation should evolve toward checking:

- Claim grounding
- Framework completeness
- Cross-section consistency
- Citation integrity
- Recommendation support
- Evidence gaps

Failed validation may be shown as job/result status, but failed candidate report content should not become workspace content.

## Frontend Rules

The frontend should remain a work application, not a marketing landing page.

Landing page:

- Left side: structured project intake
- Right side: upload supporting files first, recent projects below
- No prototype disclaimer banners
- No structured-intake banner chip
- No "What this prototype demonstrates" section

Workspace:

- Latest published version opens by default
- All seven Cs expanded by default
- No KPI/stat card strip
- Section regeneration controls should appear after a published version exists
- History should show published versions only
- Export actions should show job status

## Local Development

Default local URLs:

- Backend: `http://127.0.0.1:8005`
- Frontend: `http://localhost:3005`
- API docs: `http://127.0.0.1:8005/docs`

Common commands:

```powershell
npm install
npm run lint
npm run build
```

Backend checks should use the Python environment under `apps/api/.venv` when available.

Examples:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests
apps/api/.venv/Scripts/python.exe -m ruff check apps/api
```

If Ruff cannot write cache files because of OneDrive permissions, set `RUFF_CACHE_DIR` to a writable temporary directory and rerun.

## Editing Guidance

- Keep changes scoped to the requested behavior.
- Preserve the candidate -> validation -> publish separation.
- Do not expose draft candidate content in workspace responses.
- Do not add new upload file types without updating product requirements, backend validation, parser behavior, frontend copy, and tests together.
- Prefer existing service modules and API route patterns.
- Add or update tests when changing generation, validation, upload, publish, workspace, or export behavior.
