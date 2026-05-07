# Competitor Analysis Implementation Plan

## Product Direction

Competitor Analysis is a production-quality rebuild of the supplied `competitor-mapping-tool` HTML prototype. The MVP includes all prototype tabs:

- Competitor Map
- Pipeline
- Timeline
- Knowledge Graph

The app should match the broader Strategic Mapping design language: warm off-white surfaces, teal primary accents, compact professional layouts, Satoshi/Cabinet Grotesk-style typography, and a work-focused interface.

## Stack

Use the same app style as the Strategic Mapping tool:

- Frontend: Next.js + TypeScript
- Backend: FastAPI
- Shared package: TypeScript constants/types/schemas
- Database: Snowflake from day one
- AI: backend-only OpenAI integration
- Exports: backend-generated PDF and PowerPoint

Authentication is omitted for MVP.

## Repository Shape

Planned structure:

```text
apps/
  web/
  api/
packages/
  shared/
docs/
outputs/              # ignored; local generation JSON/debug output
```

## Persistence

Use the existing Snowflake connection/configuration pattern from the Strategic Mapping/RAG environment.

Primary persistence rules:

- Use existing `STRATEGIC_WORKSPACE` table in `COMMUNICATIONS__EU__DER__DEV / DEV` for all workspace/project state and 4-pass generation JSON outputs where possible.
- Create new `COMPETITOR_ANALYSIS_...` tables only for structured/searchable indexes and operational records.
- Store local generation/debug JSON in `outputs/`, which is ignored by Git.

Proposed app-specific tables:

- `COMPETITOR_ANALYSIS_PROJECT_INDEX`
- `COMPETITOR_ANALYSIS_EVIDENCE_ITEMS`
- `COMPETITOR_ANALYSIS_SOURCE_RUNS`
- `COMPETITOR_ANALYSIS_EXPORT_JOBS`
- `COMPETITOR_ANALYSIS_AUDIT_LOG`

Evidence records should store normalized fields and the raw source payload JSON.

## Project Model

The app supports multiple saved projects/workspaces. Each project has:

- One competitor map
- One primary asset
- Linked competitors across map, pipeline, timeline, evidence, and knowledge graph data
- JSON import/export for project sharing
- Blank initial state
- Optional load sample demo data action

Project intake fields:

- Disease / indication
- Asset or compound of interest
- Mechanism/modality
- Custom geography or market
- Time horizon
- Known competitors, optional
- Strategic question/objective

Discovery starts explicitly through a user action such as `Run Discovery`.

## Discovery And Evidence

Competitors may be:

- Suggested by discovery from validated sources
- Added manually by the user
- Enriched later through source refresh

Discovery suggestions must be reviewable before adding. Users can approve one by one or bulk approve selected suggestions. Each suggestion should include detailed rationale and source links.

Validated source families for MVP:

- PubMed
- ClinicalTrials.gov
- FDA
- EMA
- Company pipeline pages and press releases
- Congress abstracts
- Guidelines
- HTA/payer sources
- Reputable news

Trusted-source rules can auto-validate evidence. Users should have an evidence review screen where they can inspect, filter, and exclude evidence. Evidence refresh is user-triggered only.

## Four-Pass Generation Pipeline

Every AI output must run through the orchestrated four-pass generation system.

The orchestrator:

- Starts every generation or regeneration run.
- Identifies task requirements, target frontend template, required sections, and source families.
- Calls retrieval/connectors/tools.
- Sets up the Pass 1 prompt.
- Persists every intermediary input and output as JSON in Snowflake and locally under `outputs/`.
- Repeats targeted sections when Pass 4 detects missing sections or template gaps.

Passes:

- `PASS1`: Generate structured JSON data required by the tool.
- `PASS2`: Validate Pass 1 output against orchestrator requirements, template contract, evidence expectations, and completeness rules.
- `PASS3`: Run another AI/tool-calling pass to recreate Pass 1 using Pass 1, Pass 2, and orchestrator-selected data sources.
- `PASS4`: Redesign/transform Pass 3 output into the exact frontend template/view model.

Regeneration creates a new generation run linked to the prior run and preserves all intermediate JSON.

This pipeline applies to all AI outputs, including:

- Competitor discovery
- Map insights
- Pipeline analysis
- Timeline interpretation
- Knowledge graph synthesis
- Export narratives
- Strategic summaries and recommendations

## Competitor Map

MVP requirements:

- X/Y axis scale remains `-100` to `100`.
- Users can reposition competitors by both sliders and direct map dragging.
- One primary asset per map.
- Quadrant names are customizable.
- Insights are both rule-based and AI-generated.
- PNG map export can exist in the UI, but priority exports are backend PDF/PPT.

## Pipeline

Pipeline entries are connected to the same competitors shown on the map.

Fields:

- Company
- Candidate / asset name
- Mechanism of action
- Modality
- Route of administration
- Dosing frequency
- Development phase
- Trial name
- NCT ID
- Indication / patient segment
- Geography / market
- Anticipated launch
- Launch rationale / source
- Key efficacy signal
- Key safety/tolerability signal
- Differentiating claims
- Likely positioning
- Threat level
- Threat rationale
- Source evidence links
- Last refreshed date

The comparison grid should be editable inline like the prototype. Use predefined categories for mechanism, ROA, phase, and threat level while preserving room for custom values.

## Timeline

MVP requirements:

- Real ClinicalTrials.gov integration in v1.
- Launch date supports both user-entered estimates and calculated/inferred estimates from trial dates.
- Imported trial records are not manually editable after import.
- Manual records may still be used for planning/demo workflows if clearly labeled.

## Knowledge Graph

MVP requirements:

- Real PubMed search in v1.
- NCBI API key/email support through backend environment variables.
- Graph nodes include articles, authors, MeSH terms, compounds, companies, and trials.
- Clicking a node opens an in-app detail panel and provides external source links.
- Sample data is available on demand, but projects start blank.

## AI Outputs

Real OpenAI-powered analysis is required through the backend.

AI should generate:

- Strategic summary
- Threat assessment
- White-space opportunities
- Positioning recommendations
- Report narrative

AI may use all relevant data: user-entered data, PubMed, ClinicalTrials.gov, and all other validated evidence sources. Outputs should distinguish sourced facts from inference.

OpenAI configuration:

- Read `OPENAI_API_KEY` and `OPENAI_MODEL` from backend environment variables.
- Keep API keys server-side only.
- Use structured JSON output for Pass 1 and Pass 3.
- Preserve deterministic fallback output for local development when `OPENAI_API_KEY` is not configured.

## Exports

Backend-generated PowerPoint and PDF exports are required.

Exports should use the same design language as the app and include:

- Executive summary
- Competitor map
- Pipeline comparison
- Timeline
- Knowledge graph snapshot
- Evidence appendix
- AI strategic recommendations
- Methodology / source list

## Initial Build Phases

1. Scaffold monorepo structure and shared types.
2. Implement FastAPI config using existing Snowflake connection pattern.
3. Add Snowflake setup SQL for `COMPETITOR_ANALYSIS_...` index/operational tables.
4. Build blank Next.js shell with tabs and Strategic Mapping visual language.
5. Implement project intake, save/load through backend, and `STRATEGIC_WORKSPACE` persistence.
6. Build Competitor Map tab with editable competitors, one primary asset, draggable canvas, quadrant labels, and rule-based insights.
7. Build Pipeline tab with linked competitors and editable comparison grid.
8. Build Timeline tab with ClinicalTrials.gov connector and non-editable imported trials.
9. Build Knowledge Graph tab with PubMed connector and in-app node details.
10. Implement evidence review/exclusion screen.
11. Implement four-pass orchestrator and apply it to all AI output workflows.
12. Implement backend PDF/PPT exports.
13. Add tests, screenshots, and build verification.

## Open Items

- Exact Snowflake column names and existing `STRATEGIC_WORKSPACE` contract need inspection before schema implementation.
- Exact OpenAI model and prompt templates need selection.
- FDA/EMA/company/news connector depth may need phased implementation depending on available APIs and access constraints.
