# Competitor Analysis

Production-oriented competitor intelligence workspace for market mapping, pipeline analysis,
clinical timeline tracking, evidence review, knowledge graph exploration, AI synthesis, and
backend-generated exports.

## Local Apps

- Web: Next.js + TypeScript in `apps/web`
- API: FastAPI in `apps/api`
- Shared contracts: `packages/shared`

Default development ports:

- Web: `http://127.0.0.1:3006`
- API: `http://127.0.0.1:8006`
- API docs: `http://127.0.0.1:8006/docs`

## Commands

```powershell
npm install
npm run build
npm run dev
```

```powershell
apps/api/.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8006 --app-dir apps/api
```
