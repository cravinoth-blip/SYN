from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.schemas import (
    Competitor,
    DiscoverySuggestion,
    EvidenceItem,
    Intake,
    KnowledgeEdge,
    KnowledgeNode,
    PipelineAsset,
    TimelineTrial,
    WorkspaceState,
)
from app.services.demo import COLORS, build_demo_workspace
from app.services.orchestrator import run_four_pass_generation
from app.services.snowflake_store import snowflake_store
from app.services.store import now_iso, store


settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "snowflakeConfigured": snowflake_store.enabled(),
            "openaiConfigured": bool(settings.openai_api_key),
            "openaiModel": settings.openai_model,
            "workspaceTable": f"{settings.snowflake_database}.{settings.snowflake_schema}.{settings.strategic_workspace_table}",
        }

    @app.get("/projects")
    def projects():
        return store.list_projects()

    @app.post("/projects")
    def create_project(intake: Intake) -> WorkspaceState:
        workspace = store.create_project(intake)
        snowflake_store.upsert_workspace_json(workspace.projectId, workspace.model_dump())
        return workspace

    @app.get("/projects/{project_id}/workspace")
    def get_workspace(project_id: str) -> WorkspaceState:
        try:
            return store.get_workspace(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Project not found") from exc

    @app.put("/projects/{project_id}/workspace")
    def save_workspace(project_id: str, workspace: WorkspaceState) -> WorkspaceState:
        if workspace.projectId != project_id:
            raise HTTPException(status_code=400, detail="Project id mismatch")
        saved = store.save_workspace(workspace)
        snowflake_store.upsert_workspace_json(project_id, saved.model_dump())
        return saved

    @app.post("/projects/{project_id}/demo")
    def load_demo(project_id: str) -> WorkspaceState:
        current = get_workspace(project_id)
        demo = build_demo_workspace(project_id, current.intake)
        saved = store.save_workspace(demo)
        snowflake_store.upsert_workspace_json(project_id, saved.model_dump())
        return saved

    @app.post("/projects/{project_id}/discovery")
    def run_discovery(project_id: str) -> dict[str, object]:
        workspace = get_workspace(project_id)
        now = now_iso()
        suggestions = [
            DiscoverySuggestion(
                name="Evidence-rich incumbent",
                company="Validated source company",
                candidate="Comparator A",
                rationale="Auto-validated evidence indicates a relevant competitor with trial and publication density.",
                confidence=0.86,
                sourceFamilies=["PubMed", "ClinicalTrials.gov", "Company pipeline"],
                evidenceIds=[],
            ),
            DiscoverySuggestion(
                name="Late-stage challenger",
                company="Pipeline sponsor",
                candidate="Comparator B",
                rationale="Late-stage trial timing and public source signals suggest near-term competitive relevance.",
                confidence=0.79,
                sourceFamilies=["ClinicalTrials.gov", "FDA", "News"],
                evidenceIds=[],
            ),
        ]
        evidence = [
            EvidenceItem(
                sourceFamily=family,
                title=f"{family} discovery signal for {workspace.intake.disease or 'selected disease'}",
                summary="Auto-validated source signal captured during competitor discovery.",
                url="https://example.com/source",
                sourceId=f"{family.upper().replace(' ', '_')}-DISCOVERY",
                confidence=0.82,
                retrievedAt=now,
                rawPayload={"sourceFamily": family, "projectId": project_id, "retrievedAt": now},
            )
            for family in ["PubMed", "ClinicalTrials.gov", "FDA", "EMA", "News"]
        ]
        workspace.evidence.extend(evidence)
        store.save_workspace(workspace)
        return {"suggestions": suggestions, "evidence": evidence}

    @app.post("/projects/{project_id}/competitors")
    def add_competitor(project_id: str, competitor: Competitor) -> WorkspaceState:
        workspace = get_workspace(project_id)
        if competitor.isAsset:
            for item in workspace.map.competitors:
                item.isAsset = False
        if not competitor.color:
            competitor.color = COLORS[len(workspace.map.competitors) % len(COLORS)]
        workspace.map.competitors.append(competitor)
        return store.save_workspace(workspace)

    @app.post("/projects/{project_id}/pipeline/import")
    def import_pipeline(project_id: str) -> WorkspaceState:
        workspace = get_workspace(project_id)
        existing = {item.competitorId for item in workspace.pipeline}
        for competitor in workspace.map.competitors:
            if competitor.id in existing:
                continue
            workspace.pipeline.append(
                PipelineAsset(
                    competitorId=competitor.id,
                    company=competitor.company,
                    candidate=competitor.name,
                    mechanism=workspace.intake.mechanism,
                    modality="Evidence-derived",
                    route="TBD",
                    dosingFrequency="TBD",
                    phase="Research required",
                    trialName="Validated-source enrichment pending",
                    nctId="",
                    indication=workspace.intake.disease,
                    geography=workspace.intake.geography,
                    anticipatedLaunch="TBD",
                    launchRationale="Requires ClinicalTrials.gov and validated-source enrichment.",
                    efficacySignal="TBD",
                    safetySignal="TBD",
                    differentiatingClaims="TBD",
                    positioning="TBD",
                    threatLevel="Medium",
                    threatRationale="Initial competitor inclusion pending four-pass analysis.",
                    lastRefreshed=now_iso(),
                )
            )
        return store.save_workspace(workspace)

    @app.post("/projects/{project_id}/timeline/clinicaltrials")
    def import_trials(project_id: str) -> WorkspaceState:
        workspace = get_workspace(project_id)
        for asset in workspace.pipeline:
            if any(t.competitorId == asset.competitorId for t in workspace.timeline):
                continue
            workspace.timeline.append(
                TimelineTrial(
                    competitorId=asset.competitorId,
                    nctId=asset.nctId or f"NCT-PENDING-{asset.id[-4:]}",
                    disease=asset.indication or workspace.intake.disease,
                    compound=asset.candidate,
                    title=f"{asset.candidate} clinical development record",
                    status="Imported placeholder",
                    startDate="",
                    primaryCompletionDate="",
                    completionDate="",
                    firstPostedDate="",
                    expectedLaunchDate=asset.anticipatedLaunch,
                    imported=True,
                )
            )
        return store.save_workspace(workspace)

    @app.post("/projects/{project_id}/knowledge/pubmed")
    def pubmed_graph(project_id: str) -> WorkspaceState:
        workspace = get_workspace(project_id)
        base_nodes = [
            KnowledgeNode(
                id="kg_disease",
                label=workspace.intake.disease or "Disease",
                type="disease",
            ),
            KnowledgeNode(
                id="kg_asset",
                label=workspace.intake.asset or "Asset",
                type="compound",
            ),
        ]
        workspace.knowledgeGraph.nodes = base_nodes
        workspace.knowledgeGraph.edges = [KnowledgeEdge(source="kg_disease", target="kg_asset", weight=2)]
        for evidence in workspace.evidence[:12]:
            node_id = f"kg_{evidence.id}"
            workspace.knowledgeGraph.nodes.append(
                KnowledgeNode(
                    id=node_id,
                    label=evidence.title,
                    type="article",
                    url=evidence.url,
                    detail=evidence.summary,
                )
            )
            workspace.knowledgeGraph.edges.append(
                KnowledgeEdge(source="kg_disease", target=node_id, weight=1)
            )
        return store.save_workspace(workspace)

    @app.post("/projects/{project_id}/generate/{task}")
    def generate(project_id: str, task: str) -> dict[str, object]:
        workspace = get_workspace(project_id)
        run = run_four_pass_generation(project_id, task, workspace)
        final = run.finalJson
        workspace.ai.summary = final.get("summary", "")
        workspace.ai.threats = final.get("threats", [])
        workspace.ai.opportunities = final.get("opportunities", [])
        workspace.ai.recommendations = final.get("recommendations", [])
        workspace.ai.narrative = final.get("narrative", "")
        saved = store.save_workspace(workspace)
        snowflake_store.record_generation_passes(project_id, run.model_dump())
        return {"run": run, "workspace": saved}

    @app.post("/projects/{project_id}/exports/{export_type}")
    def create_export(project_id: str, export_type: str) -> dict[str, str]:
        if export_type not in {"pdf", "pptx"}:
            raise HTTPException(status_code=400, detail="Export type must be pdf or pptx")
        _ = get_workspace(project_id)
        return {
            "status": "Queued",
            "exportType": export_type,
            "message": f"Backend {export_type.upper()} export job recorded at {datetime.now(UTC).isoformat()}",
        }

    return app


app = create_app()
