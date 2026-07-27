from __future__ import annotations

from fastapi.testclient import TestClient

import main
from knowledge_search import build_filter
import research_search


class FakeSearchClient:
    def search(self, **kwargs):
        return (
            [
                {
                    "CHUNK_ID": "chunk-1",
                    "CHUNK_TEXT": "Relevant evidence",
                    "DOCUMENT_ID": "document-1",
                }
            ],
            42,
        )


class FakeResearchClient:
    def search(self, **kwargs):
        return ([{"PUBMED_ID": 123, "ARTICLE_TITLE": "Evidence"}], 55)


def setup_function():
    main.app.dependency_overrides.clear()
    main.get_client.cache_clear()
    main.get_research_client.cache_clear()


def test_health_does_not_require_credentials():
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_requires_api_key(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    response = TestClient(main.app).post("/search", json={"query": "oncology"})
    assert response.status_code == 401


def test_search_returns_cortex_results(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    main.app.dependency_overrides[main.get_client] = lambda: FakeSearchClient()
    monkeypatch.setattr(main, "get_client", lambda: FakeSearchClient())

    response = TestClient(main.app).post(
        "/search",
        headers={"X-API-Key": "correct-key"},
        json={"query": "oncology", "limit": 5, "language": "en"},
    )

    assert response.status_code == 200
    assert response.json()["result_count"] == 1
    assert response.json()["results"][0]["CHUNK_ID"] == "chunk-1"


def test_compatible_query_endpoint(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_client", lambda: FakeSearchClient())

    response = TestClient(main.app).post(
        "/query/",
        headers={"X-API-Key": "correct-key"},
        json={"query_text": "oncology", "top_k": 5},
    )

    assert response.status_code == 200
    assert response.json()["context"][0]["CHUNK_ID"] == "chunk-1"


def test_filter_is_allow_listed():
    assert build_filter(language="en") == {"@eq": {"LANGUAGE": "en"}}
    assert build_filter(language="en", document_type="PDF") == {
        "@and": [
            {"@eq": {"LANGUAGE": "en"}},
            {"@eq": {"DOCUMENT_TYPE": "PDF"}},
        ]
    }


def test_research_query_returns_snowflake_records(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_research_client", lambda: FakeResearchClient())

    response = TestClient(main.app).post(
        "/research/query/",
        headers={"X-API-Key": "correct-key"},
        json={"source": "pubmed", "query_text": "antimicrobial resistance", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["context"][0]["PUBMED_ID"] == 123


def test_research_query_rejects_unknown_source(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    response = TestClient(main.app).post(
        "/research/query/",
        headers={"X-API-Key": "correct-key"},
        json={"source": "arbitrary_table", "query_text": "infection"},
    )
    assert response.status_code == 422


def test_dynamic_discovery_extracts_approved_identifiers(monkeypatch):
    monkeypatch.setattr(
        research_search,
        "_get_json",
        lambda *args, **kwargs: {"esearchresult": {"idlist": ["123", "bad"]}},
    )
    assert research_search._discover_pubmed_ids("topic", 5) == [123]

    monkeypatch.setattr(
        research_search,
        "_get_json",
        lambda *args, **kwargs: {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {"nctId": "NCT00000001"}
                    }
                }
            ]
        },
    )
    assert research_search._discover_trial_ids("topic", 5) == ["NCT00000001"]
