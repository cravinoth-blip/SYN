from app.schemas import (
    AiState,
    Competitor,
    EvidenceItem,
    Intake,
    KnowledgeEdge,
    KnowledgeGraphState,
    KnowledgeNode,
    PipelineAsset,
    TimelineTrial,
    WorkspaceState,
)
from app.services.store import now_iso


COLORS = ["#01696f", "#964219", "#a12c7b", "#006494", "#7a39bb", "#437a22"]


def build_demo_workspace(project_id: str, intake: Intake) -> WorkspaceState:
    competitors = [
        Competitor(
            id="cmp_asset",
            name=intake.asset or "Asset X",
            company="Internal asset",
            color=COLORS[0],
            x=18,
            y=22,
            isAsset=True,
            rationale="Primary asset for strategic comparison.",
            sourceCount=4,
        ),
        Competitor(
            id="cmp_pfizer",
            name="Tafamidis",
            company="Pfizer",
            color=COLORS[1],
            x=62,
            y=58,
            rationale="Established standard with strong clinical and market footprint.",
            sourceCount=12,
        ),
        Competitor(
            id="cmp_acoramidis",
            name="Acoramidis",
            company="BridgeBio",
            color=COLORS[2],
            x=48,
            y=34,
            rationale="Late-stage competitor with differentiated stabilization narrative.",
            sourceCount=9,
        ),
        Competitor(
            id="cmp_vutrisiran",
            name="Vutrisiran",
            company="Alnylam",
            color=COLORS[3],
            x=-34,
            y=66,
            rationale="Silencing modality creates a distinct clinical positioning axis.",
            sourceCount=10,
        ),
    ]
    evidence = [
        EvidenceItem(
            sourceFamily="PubMed",
            title="Clinical evidence review for ATTR-CM therapies",
            summary="Peer-reviewed literature supports differentiation by outcome strength, modality, and administration burden.",
            url="https://pubmed.ncbi.nlm.nih.gov/",
            sourceId="PMID-DEMO-1",
            confidence=0.86,
            retrievedAt=now_iso(),
            rawPayload={"demo": True, "source": "PubMed"},
        ),
        EvidenceItem(
            sourceFamily="ClinicalTrials.gov",
            title="Late-stage ATTR-CM trial landscape",
            summary="Trial timing and completion milestones indicate near-term competitive pressure.",
            url="https://clinicaltrials.gov/",
            sourceId="NCT-DEMO-1",
            confidence=0.88,
            retrievedAt=now_iso(),
            rawPayload={"demo": True, "source": "ClinicalTrials.gov"},
        ),
    ]
    pipeline = [
        PipelineAsset(
            competitorId=c.id,
            company=c.company,
            candidate=c.name,
            mechanism="TTR stabilization" if c.id != "cmp_vutrisiran" else "TTR silencing",
            modality="Small molecule" if c.id != "cmp_vutrisiran" else "RNAi",
            route="Oral" if c.id != "cmp_vutrisiran" else "Subcutaneous",
            dosingFrequency="Daily" if c.id != "cmp_vutrisiran" else "Every 3 months",
            phase="Launched" if c.id == "cmp_pfizer" else "Phase 3",
            trialName="Demo pivotal trial",
            nctId=f"NCT-DEMO-{idx}",
            indication=intake.disease or "ATTR-CM",
            geography=intake.geography or "Global",
            anticipatedLaunch="Marketed" if c.id == "cmp_pfizer" else "2026",
            launchRationale="Derived from demo trial timing and public milestone assumptions.",
            efficacySignal="Cardiovascular outcome and functional endpoint signal.",
            safetySignal="Monitor tolerability and discontinuation profile.",
            differentiatingClaims="Differentiates by route, outcome confidence, and patient fit.",
            positioning="Evidence-backed competitive option.",
            threatLevel="High" if not c.isAsset else "Medium",
            threatRationale="High relevance to the selected disease and modality space.",
            sourceLinks=[item.url for item in evidence],
            lastRefreshed=now_iso(),
        )
        for idx, c in enumerate(competitors, start=1)
    ]
    timeline = [
        TimelineTrial(
            competitorId=asset.competitorId,
            nctId=asset.nctId,
            disease=asset.indication,
            compound=asset.candidate,
            title=f"{asset.candidate} outcomes study",
            status="Recruiting" if asset.phase != "Launched" else "Completed",
            startDate="2024-01",
            primaryCompletionDate="2026-06",
            completionDate="2026-12",
            firstPostedDate="2023-11-10",
            expectedLaunchDate=asset.anticipatedLaunch,
            imported=True,
        )
        for asset in pipeline
    ]
    nodes = [
        KnowledgeNode(id="disease", label=intake.disease or "ATTR-CM", type="disease", detail="Disease scope"),
        KnowledgeNode(id="asset", label=intake.asset or "Asset X", type="compound", detail="Primary asset"),
    ]
    edges = [KnowledgeEdge(source="disease", target="asset", weight=2)]
    for item in evidence:
        nodes.append(KnowledgeNode(id=item.id, label=item.title, type="article", url=item.url, detail=item.summary))
        edges.append(KnowledgeEdge(source="disease", target=item.id, weight=1))
    return WorkspaceState(
        projectId=project_id,
        intake=intake,
        map={
            "title": "Competitor Mapping:",
            "subtitle": "Defining Strategic Positioning by Understanding Market Drivers",
            "xAxis": "Clinical differentiation",
            "yAxis": "Market access leverage",
            "framingQuestion": "Where is the most defensible white space?",
            "quadrantNames": ("Defend", "Lead", "Monitor", "Reposition"),
            "competitors": competitors,
            "strategyNotes": [
                "Protect high-evidence positioning where current market leaders are strongest.",
                "Use administration and patient-fit differences to create credible white space.",
                "Refresh evidence after major trial readouts or regulatory milestones.",
            ],
        },
        pipeline=pipeline,
        timeline=timeline,
        evidence=evidence,
        knowledgeGraph=KnowledgeGraphState(nodes=nodes, edges=edges),
        ai=AiState(
            summary="The demo landscape shows a crowded evidence-led market where differentiation must combine outcomes, route, and access strategy.",
            threats=["Established incumbent evidence", "Late-stage launch timing", "Alternative modality narrative"],
            opportunities=["Patient segment focus", "Administration burden reduction", "Evidence gap ownership"],
            recommendations=[
                "Prioritize claims that connect clinical signal to patient selection.",
                "Track late-stage trial milestones and expected launch timing.",
                "Use evidence review exclusions before regenerating strategic analysis.",
            ],
            narrative="This narrative is generated from demo evidence and should be replaced by a four-pass run for live projects.",
        ),
    )
