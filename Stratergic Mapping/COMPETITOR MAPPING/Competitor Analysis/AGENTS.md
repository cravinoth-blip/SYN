# AGENTS.md

Guidance for AI agents and coding assistants working in this repository.

## Active Repository Context

Use this `Competitor Analysis` repository as the only active workspace for this project.

- The repository lives at `C:\Users\a287484\OneDrive - Syneos Health\Desktop\Stratergic Mapping\COMPETITOR MAPPING\Competitor Analysis`.
- The sibling `Stratergic Mapping` repository is a design and architecture reference, not the active workspace.
- Run reads, writes, commands, tests, builds, and repo-status checks from this repository unless the user explicitly asks otherwise.
- Do not create or update files in `RAG` or the parent `Stratergic Mapping` app for Competitor Analysis work unless the user asks.
- If a session starts from another working directory, switch context to this repository before acting.

## Project

This repo implements the Competitor Analysis app, a production-quality recreation of the supplied `competitor-mapping-tool` HTML prototype.

The MVP must include all prototype tabs:

- Competitor Map
- Pipeline
- Timeline
- Knowledge Graph

Use the existing `Stratergic Mapping` application as the architectural and visual reference. The app should feel like a companion work tool in the same product family, not a marketing page or a disposable prototype.

Expected stack:

- `apps/web`: Next.js + TypeScript frontend
- `apps/api`: FastAPI backend
- `packages/shared`: shared constants, schemas, and TypeScript types
- `docs`: product, architecture, and implementation notes

Add worker or infra folders only when the implementation actually needs them.

## Product Goals

The app helps users analyze competitive dynamics across market positioning, pipeline assets, clinical timelines, and scientific evidence.

Core workflows:

- Build a competitor quadrant map with editable axes, competitors, strategic notes, and asset markers.
- Track competitor pipeline assets by company, candidate, phase, launch timing, profile, route, positioning, and threat.
- Track clinical development timelines using manual records first, then ClinicalTrials.gov integration when enabled.
- Explore disease and compound literature through a PubMed-backed knowledge graph.
- Generate strategic analysis from the entered and retrieved evidence when AI features are enabled.
- Export useful outputs for presentation and downstream strategy work.

## Generation Orchestration

Every AI generation and regeneration workflow must run through an orchestrated four-pass pipeline.

The orchestrator owns the generation run. It must:

- Begin the process and create a generation run record.
- Identify the task requirements, target frontend template, required sections, and data source families.
- Call retrieval/connectors/tools needed for the generation.
- Prepare the prompt and structured requirements for Pass 1.
- Persist every intermediary input and output as JSON.
- Decide whether missing or invalid sections require a targeted repeat of the pipeline.

Pass requirements:

- `PASS1`: Generate the data needed for the tool and produce structured JSON output.
- `PASS2`: Validate the Pass 1 JSON against the orchestrator requirements, template contract, evidence expectations, and completeness rules.
- `PASS3`: Run another AI LLM tool-calling pass that recreates the Pass 1 output using Pass 1 output, Pass 2 validation output, and the orchestrator-selected data sources as inputs.
- `PASS4`: Transform the Pass 3 output into the exact frontend template/view model required by the app.

If Pass 4 detects missing sections or template gaps, the orchestrator must repeat the process for the missing section(s). Do not patch missing AI-generated sections directly in the frontend.

Regeneration must be supported. A regeneration creates a new generation run linked to the prior run, preserving the original intermediary JSON outputs.

All intermediary step outputs must be saved as JSON and be inspectable for debugging, audit, and evidence review.

## Non-Negotiable MVP Rules

- Recreate all four tabs for MVP.
- Preserve the core design language of the existing `Stratergic Mapping` tool.
- Do not copy the single-file prototype structure forward; rebuild as typed, maintainable app modules.
- Treat the supplied HTML as a behavioral and visual reference. It contains duplicated HTML/CSS/script blocks that should not be preserved.
- Keep the UI dense, practical, and work-focused.
- The first screen should be the usable app workspace, not a landing page.
- Add real persistence rather than relying on global inline JavaScript state.
- Keep API keys and AI/provider secrets out of browser code.
- Prefer typed schemas shared between frontend and backend.

## Architecture Expectations

Backend service boundaries should remain clear:

- Project/workspace service
- Competitor map service
- Pipeline service
- Timeline/trial service
- Knowledge graph service
- External source connector service
- PubMed connector
- ClinicalTrials.gov connector
- AI analysis service
- Export service
- Audit/activity logging

Prefer extending these boundaries over creating unrelated parallel paths.

Frontend structure should separate:

- Route/page shells
- Feature components by tab
- Canvas/chart rendering components
- Forms and controls
- Client API layer
- State management
- Shared UI primitives
- Design tokens/theme

## Data Model

Snowflake is the primary database from day one. Use the existing Snowflake connection/configuration pattern from the broader Strategic Mapping/RAG environment.

Use the existing `STRATEGIC_WORKSPACE` table in `COMMUNICATIONS__EU__DER__DEV / DEV` where it fits the workspace/intermediary JSON persistence model. Do not create a separate generation pass output table unless the existing table cannot support the required access pattern or the user approves the change.

Create new app-specific Snowflake tables with the `COMPETITOR_ANALYSIS_` prefix for data that does not belong in `STRATEGIC_WORKSPACE`.

Core entities:

- `project`
- `competitor_map`
- `map_competitor`
- `strategy_note`
- `pipeline_asset`
- `timeline_trial`
- `knowledge_graph_query`
- `knowledge_graph_article`
- `knowledge_graph_node`
- `knowledge_graph_edge`
- `analysis_result`
- `generation_run`
- `generation_pass_output`
- `generation_section_status`
- `export_job`
- `audit_log`

Use JSON-style fields for flexible metadata, source payloads, graph layout, and user-defined dimensions.

## External Evidence Rules

External integrations should be behind backend connectors.

Primary sources:

- PubMed / NCBI E-utilities for the Knowledge Graph tab
- ClinicalTrials.gov API v2 for the Timeline tab

Source records should be normalized before UI or AI features consume them. Preserve source identifiers such as PMID and NCT ID.

Evidence labels should distinguish:

- `SourceBacked`
- `UserEntered`
- `AIInference`

AI-generated recommendations must not be presented as sourced facts unless tied to source-backed evidence.

## Frontend Rules

The frontend should remain a sophisticated work application.

- Match the Strategic Mapping design language: restrained professional layout, warm surfaces, teal primary accents, careful typography, and compact controls.
- Use tabs for the main sections.
- Use icon buttons where appropriate, with accessible labels/tooltips.
- Prefer direct manipulation for the map: sliders plus draggable canvas points.
- Keep charts and canvas views responsive and nonblank across desktop and mobile widths.
- Use empty, loading, and error states for every tab.
- Avoid in-app explanatory marketing copy.
- Avoid nested cards and oversized decorative sections.

## Feature Expectations By Tab

### Competitor Map

- Editable map title, subtitle, X axis, Y axis, and strategic framing question.
- Add, delete, rename, recolor, and reposition competitors.
- Mark one or more assets only if product requirements allow it; otherwise default to one primary asset.
- Support slider movement and direct canvas dragging.
- Display strategy notes and rule-based insight cards.
- Export the map to PNG.

### Pipeline

- Add, edit, and delete pipeline assets.
- Include fields for company, candidate, phase, trial, anticipated launch, compound/profile characteristics, route, positioning, threat, and profile class.
- Render an editable comparison grid.
- Generate charts from actual pipeline data rather than static sample charts.

### Timeline

- Support manual trial records in MVP.
- Prepare for ClinicalTrials.gov API import through the backend.
- Include disease and compound filters, sorting, and configurable years-ahead horizon.
- Preserve NCT IDs and trial date fields.

### Knowledge Graph

- Support sample data and backend PubMed search.
- Build graph nodes and edges from normalized article data.
- Include article list, graph stats, source links, and hover/detail interactions.
- Keep force layout logic isolated from UI components.

## AI Rules

AI analysis should run through the backend, not directly in the browser.

AI features may generate:

- Strategic summary
- Threat assessment
- White-space opportunities
- Positioning recommendations
- Evidence gaps
- Suggested next questions

AI output should cite or reference the app data it used where possible, and should clearly separate sourced facts from inference.

## Local Development

Default local URLs should follow the Strategic Mapping convention unless a port conflict requires a change:

- Backend: `http://127.0.0.1:8005` or the next available API port
- Frontend: `http://localhost:3005` or the next available web port
- API docs: `http://127.0.0.1:<api-port>/docs`

Expected commands once scaffolded:

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
- Prefer existing service modules, API route patterns, and shared schemas once they exist.
- Add tests when changing persistence, API contracts, connector behavior, AI analysis, export behavior, or nontrivial data transformations.
- Do not expose secrets in frontend code.
- Do not introduce live external API calls in tests unless explicitly marked/integrated.
- Preserve user-entered project data during migrations or schema changes.
