from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Intake(BaseModel):
    projectName: str = ""
    disease: str = ""
    asset: str = ""
    mechanism: str = ""
    geography: str = ""
    timeHorizon: str = ""
    knownCompetitors: str = ""
    objective: str = ""


class Competitor(BaseModel):
    id: str = Field(default_factory=lambda: new_id("cmp"))
    name: str
    company: str = ""
    color: str = "#01696f"
    x: int = 0
    y: int = 0
    isAsset: bool = False
    rationale: str = ""
    sourceCount: int = 0


class PipelineAsset(BaseModel):
    id: str = Field(default_factory=lambda: new_id("pipe"))
    competitorId: str
    company: str = ""
    candidate: str = ""
    mechanism: str = ""
    modality: str = ""
    route: str = ""
    dosingFrequency: str = ""
    phase: str = ""
    trialName: str = ""
    nctId: str = ""
    indication: str = ""
    geography: str = ""
    anticipatedLaunch: str = ""
    launchRationale: str = ""
    efficacySignal: str = ""
    safetySignal: str = ""
    differentiatingClaims: str = ""
    positioning: str = ""
    threatLevel: Literal["Low", "Medium", "High"] = "Medium"
    threatRationale: str = ""
    sourceLinks: list[str] = Field(default_factory=list)
    lastRefreshed: str = ""


class TimelineTrial(BaseModel):
    id: str = Field(default_factory=lambda: new_id("trial"))
    competitorId: str = ""
    nctId: str = ""
    disease: str = ""
    compound: str = ""
    title: str = ""
    status: str = ""
    startDate: str = ""
    primaryCompletionDate: str = ""
    completionDate: str = ""
    firstPostedDate: str = ""
    expectedLaunchDate: str = ""
    imported: bool = True


class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ev"))
    sourceFamily: str
    title: str
    summary: str
    url: str = ""
    sourceId: str = ""
    confidence: float = 0.8
    validationStatus: Literal["AutoValidated", "Excluded", "NeedsReview"] = "AutoValidated"
    evidenceLabel: Literal["SourceBacked", "UserEntered", "AIInference"] = "SourceBacked"
    retrievedAt: str
    rawPayload: dict[str, Any] = Field(default_factory=dict)


class KnowledgeNode(BaseModel):
    id: str
    label: str
    type: Literal["article", "author", "mesh", "compound", "company", "trial", "disease"]
    url: str = ""
    detail: str = ""


class KnowledgeEdge(BaseModel):
    source: str
    target: str
    weight: int = 1


class MapState(BaseModel):
    title: str = "Competitor Mapping:"
    subtitle: str = "Defining Strategic Positioning by Understanding Market Drivers"
    xAxis: str = "Market Driver 1"
    yAxis: str = "Market Driver 2"
    framingQuestion: str = "What if the top two drivers are taken?"
    quadrantNames: tuple[str, str, str, str] = (
        "Defend",
        "Lead",
        "Monitor",
        "Reposition",
    )
    competitors: list[Competitor] = Field(default_factory=list)
    strategyNotes: list[str] = Field(default_factory=list)


class AiState(BaseModel):
    summary: str = ""
    threats: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    narrative: str = ""


class KnowledgeGraphState(BaseModel):
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)


class WorkspaceState(BaseModel):
    projectId: str
    intake: Intake
    map: MapState = Field(default_factory=MapState)
    pipeline: list[PipelineAsset] = Field(default_factory=list)
    timeline: list[TimelineTrial] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    knowledgeGraph: KnowledgeGraphState = Field(default_factory=KnowledgeGraphState)
    ai: AiState = Field(default_factory=AiState)


class ProjectRecord(BaseModel):
    projectId: str = Field(default_factory=lambda: new_id("proj"))
    projectName: str
    disease: str
    asset: str
    geography: str
    updatedAt: str


class DiscoverySuggestion(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sug"))
    name: str
    company: str
    candidate: str
    rationale: str
    confidence: float
    sourceFamilies: list[str]
    evidenceIds: list[str]


class GenerationRun(BaseModel):
    runId: str = Field(default_factory=lambda: new_id("gen"))
    projectId: str
    task: str
    status: str
    passOutputs: list[dict[str, Any]]
    finalJson: dict[str, Any]
