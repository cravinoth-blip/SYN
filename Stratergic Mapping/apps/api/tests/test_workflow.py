import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("LIVE_CONNECTORS_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.common import SECTION_GUIDANCE
from app.services.connectors import build_connectors
from app.services.connectors.source_connectors import _parse_pmc_xml, _parse_pubmed_xml


client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_connector_inventory_includes_all_source_families() -> None:
    db = SessionLocal()
    try:
        source_types = [connector.source_type for connector in build_connectors(db)]
    finally:
        db.close()

    assert source_types == [
        "InternalUpload",
        "PubMed",
        "PMC",
        "ClinicalTrials",
        "Guideline",
        "Regulatory",
        "HTA",
        "Epidemiology",
        "Congress",
        "News",
        "Advocacy",
    ]


def test_pubmed_xml_parser_extracts_abstract_metadata_and_citation() -> None:
    records = _parse_pubmed_xml(
        """
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID>12345</PMID>
              <Article>
                <Journal>
                  <Title>Journal of Testing</Title>
                  <JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue>
                </Journal>
                <ArticleTitle>EGFR exon 20 treatment landscape</ArticleTitle>
                <Abstract>
                  <AbstractText Label="Background">Important background.</AbstractText>
                  <AbstractText>Key results.</AbstractText>
                </Abstract>
                <AuthorList>
                  <Author><LastName>Smith</LastName><Initials>AB</Initials></Author>
                </AuthorList>
              </Article>
            </MedlineCitation>
            <PubmedData>
              <ArticleIdList><ArticleId IdType="doi">10.1000/test</ArticleId></ArticleIdList>
            </PubmedData>
          </PubmedArticle>
        </PubmedArticleSet>
        """
    )

    assert records[0]["id"] == "12345"
    assert "Important background" in records[0]["text"]
    assert records[0]["raw_payload"]["doi"] == "10.1000/test"
    assert "PMID: 12345" in records[0]["citation"]


def test_pmc_xml_parser_extracts_full_text_and_citation() -> None:
    records = _parse_pmc_xml(
        """
        <pmc-articleset>
          <article>
            <front>
              <journal-meta><journal-title>PMC Journal</journal-title></journal-meta>
              <article-meta>
                <article-id pub-id-type="pmc">99999</article-id>
                <article-id pub-id-type="pmid">88888</article-id>
                <title-group><article-title>Full text article</article-title></title-group>
                <contrib-group>
                  <contrib contrib-type="author">
                    <name><surname>Jones</surname><given-names>CD</given-names></name>
                  </contrib>
                </contrib-group>
                <pub-date><year>2023</year></pub-date>
                <abstract><p>Abstract text.</p></abstract>
              </article-meta>
            </front>
            <body><sec><title>Results</title><p>Full body evidence text.</p></sec></body>
          </article>
        </pmc-articleset>
        """
    )

    assert records[0]["id"] == "99999"
    assert "Abstract text" in records[0]["text"]
    assert "Full body evidence text" in records[0]["text"]
    assert records[0]["url"] == "https://pmc.ncbi.nlm.nih.gov/articles/PMC99999/"
    assert "PMCID: PMC99999" in records[0]["citation"]


@pytest.mark.asyncio
async def test_connectors_default_to_100_records_when_live_disabled() -> None:
    db = SessionLocal()
    try:
        connectors = {
            connector.source_type: connector
            for connector in build_connectors(db)
            if connector.source_type in {"PubMed", "PMC", "ClinicalTrials", "Guideline"}
        }
    finally:
        db.close()

    plan = {
        "project_id": "project",
        "disease": "Metastatic NSCLC",
        "subtype_biomarker": "EGFR exon 20 insertion",
        "line_of_therapy": "2L+",
        "geography": "US + EU5",
        "section_name": "Competition",
        "section_guidance": SECTION_GUIDANCE["Competition"],
    }

    pubmed = await connectors["PubMed"].retrieve(plan)
    pmc = await connectors["PMC"].retrieve(plan)
    clinical_trials = await connectors["ClinicalTrials"].retrieve(plan)
    guideline = await connectors["Guideline"].retrieve(plan)

    assert pubmed[0].raw_payload["retmax"] == 100
    assert pmc[0].raw_payload["retmax"] == 100
    assert clinical_trials[0].raw_payload["page_size"] == 100
    assert guideline[0].raw_payload["target_results"] == 100


def test_incomplete_intake_blocks_generation() -> None:
    response = client.post(
        "/projects",
        json={
            "project_name": "Incomplete",
            "disease": "Metastatic NSCLC",
            "geography": "",
            "client_name": "Pilot",
        },
    )
    assert response.status_code == 200
    project_id = response.json()["project_id"]

    generation = client.post(f"/projects/{project_id}/generate", json={})

    assert generation.status_code == 200
    body = generation.json()
    assert body["status"] == "Failed"
    assert "Generation blocked" in body["message"]
    assert "Geography" in body["message"]


def test_generation_publishes_only_validated_workspace() -> None:
    project = client.post(
        "/projects",
        json={
            "project_name": "EGFRex20 NSCLC US+EU5 landscape",
            "disease": "Metastatic NSCLC",
            "subtype_biomarker": "EGFR exon 20 insertion",
            "line_of_therapy": "2L+",
            "geography": "US + EU5",
            "client_name": "Pilot account",
            "optional_brief": "Focus on competitor timing.",
        },
    ).json()

    job = client.post(f"/projects/{project['project_id']}/generate", json={}).json()
    assert job["status"] == "Succeeded"
    assert job["candidate_version_id"]
    assert job["version_id"]

    workspace = client.get(f"/projects/{project['project_id']}/workspace")
    assert workspace.status_code == 200
    body = workspace.json()
    assert body["latest_version"]["publish_status"] == "PUBLISHED"
    assert len(body["sections"]) == 7
    assert all(section["evidence"] for section in body["sections"])


def test_section_regeneration_creates_new_latest_version() -> None:
    project = client.post(
        "/projects",
        json={
            "project_name": "Competition regeneration",
            "disease": "Metastatic NSCLC",
            "subtype_biomarker": "EGFR exon 20 insertion",
            "line_of_therapy": "2L+",
            "geography": "US + EU5",
            "client_name": "Pilot account",
        },
    ).json()
    first_job = client.post(f"/projects/{project['project_id']}/generate", json={}).json()

    regen = client.post(
        f"/projects/{project['project_id']}/regenerate/section",
        json={
            "parent_version_id": first_job["version_id"],
            "section_name": "Competition",
            "change_instruction": "Emphasize competitor timing and exclude news.",
            "excluded_source_categories": ["News"],
            "excluded_document_ids": [],
        },
    ).json()

    assert regen["status"] == "Succeeded"
    assert regen["version_id"] != first_job["version_id"]
    workspace = client.get(f"/projects/{project['project_id']}/workspace").json()
    assert workspace["latest_version"]["version_id"] == regen["version_id"]
    assert len(workspace["history"]) == 2
