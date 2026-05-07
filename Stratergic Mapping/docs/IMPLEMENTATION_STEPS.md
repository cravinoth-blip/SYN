# Implementation Steps

1. Create monorepo foundation, local environment template, and Docker Compose services.
2. Add FastAPI backend foundation with settings, database session, health endpoint, and CORS.
3. Implement the PostgreSQL schema from the ERD with Alembic migrations.
4. Add typed API schemas and enums for projects, evidence, versions, jobs, validation, and exports.
5. Implement backend services for intake, uploads, parsing, retrieval planning, connectors, evidence, generation, regeneration, validation, versions, citations, workspace read models, exports, and audit logging.
6. Implement source adapters for internal uploads, PubMed/PMC, ClinicalTrials, guidelines, regulatory, HTA, epidemiology, congress, news, and advocacy sources.
7. Expose the planned FastAPI routes and enforce the validation hard gate.
8. Add a worker entrypoint for async orchestration and keep a local background-task path for simple development.
9. Build the Next.js app from the supplied prototype: intake, uploads, recent projects, latest workspace, all seven Cs, regeneration, history, references, and export status.
10. Add backend and frontend tests for the required acceptance scenarios.
11. Verify with lint, tests, builds, and a local Docker run.

