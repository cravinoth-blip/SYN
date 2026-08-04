from __future__ import annotations

from fastapi.testclient import TestClient

import main
from knowledge_search import build_filter


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


class FakeProductClient:
    def list_products(self, therapeutic_set=None):
        return ([{"PRODUCT_KEY": "CRESEMBA", "THERAPEUTIC_SET": "ANTIFUNGAL"}], 12)

    def product_trials(self, product_key, **kwargs):
        return ([{"PRODUCT_KEY": product_key, "NCT_ID": "NCT00000001"}], 13)

    def product_publications(self, product_key, **kwargs):
        return ([{"PRODUCT_KEY": product_key, "PUBMED_ID": "123"}], 14)

    def trial(self, nct_id):
        return ([{"NCT_ID": nct_id, "PRODUCT_KEY": "CRESEMBA"}], 15)

    def publication(self, pubmed_id):
        return ([{"PUBMED_ID": pubmed_id, "PRODUCT_KEYS": ["CRESEMBA"]}], 16)


class FakeSchemaBrowser:
    def objects(self):
        return (
            [
                {
                    "TABLE_NAME": "KNOWLEDGE_CHUNKS",
                    "TABLE_TYPE": "BASE TABLE",
                    "COLUMNS": [{"COLUMN_NAME": "CHUNK_ID", "DATA_TYPE": "TEXT"}],
                }
            ],
            20,
        )

    def rows(self, table_name, **kwargs):
        if table_name == "UNKNOWN_TABLE":
            raise ValueError("Table or view is not in PFIZER_ANTIINF")
        return ([{"RECORD": {"CHUNK_ID": "chunk-1"}}], 21)

    def search(self, query, **kwargs):
        return (
            [
                {
                    "TABLE_NAME": "KNOWLEDGE_CHUNKS",
                    "RECORD": {"CHUNK_ID": "chunk-1", "CHUNK_TEXT": query},
                }
            ],
            22,
        )


def setup_function():
    main.app.dependency_overrides.clear()
    main.get_client.cache_clear()
    main.get_product_client.cache_clear()
    main.get_schema_browser.cache_clear()


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


def test_cross_database_research_route_is_absent(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    response = TestClient(main.app).post(
        "/research/query/",
        headers={"X-API-Key": "correct-key"},
        json={"source": "pubmed", "query_text": "infection"},
    )
    assert response.status_code == 404


def test_schema_object_inventory(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_schema_browser", lambda: FakeSchemaBrowser())
    response = TestClient(main.app).get(
        "/schema/objects", headers={"X-API-Key": "correct-key"}
    )
    assert response.status_code == 200
    assert response.json()["schema"] == "PFIZER_ANTIINF"
    assert response.json()["objects"][0]["TABLE_NAME"] == "KNOWLEDGE_CHUNKS"


def test_schema_table_rows_and_search(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_schema_browser", lambda: FakeSchemaBrowser())
    client = TestClient(main.app)
    rows = client.get(
        "/schema/tables/knowledge_chunks/rows?limit=5&search=Cresemba",
        headers={"X-API-Key": "correct-key"},
    )
    search = client.post(
        "/schema/search",
        headers={"X-API-Key": "correct-key"},
        json={"query": "Cresemba", "total_limit": 10},
    )
    assert rows.status_code == 200
    assert rows.json()["table_name"] == "KNOWLEDGE_CHUNKS"
    assert search.status_code == 200
    assert search.json()["results"][0]["TABLE_NAME"] == "KNOWLEDGE_CHUNKS"


def test_schema_browser_rejects_unknown_table(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_schema_browser", lambda: FakeSchemaBrowser())
    response = TestClient(main.app).get(
        "/schema/tables/unknown_table/rows",
        headers={"X-API-Key": "correct-key"},
    )
    assert response.status_code == 422


def test_list_products_filters_set(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_product_client", lambda: FakeProductClient())
    response = TestClient(main.app).get(
        "/products/?therapeutic_set=ANTIFUNGAL",
        headers={"X-API-Key": "correct-key"},
    )
    assert response.status_code == 200
    assert response.json()["products"][0]["PRODUCT_KEY"] == "CRESEMBA"


def test_product_trials_normalises_key(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_product_client", lambda: FakeProductClient())
    response = TestClient(main.app).get(
        "/products/cresemba/trials?limit=5",
        headers={"X-API-Key": "correct-key"},
    )
    assert response.status_code == 200
    assert response.json()["product_key"] == "CRESEMBA"
    assert response.json()["trials"][0]["NCT_ID"] == "NCT00000001"


def test_product_publications(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_product_client", lambda: FakeProductClient())
    response = TestClient(main.app).get(
        "/products/CRESEMBA/publications",
        headers={"X-API-Key": "correct-key"},
    )
    assert response.status_code == 200
    assert response.json()["publications"][0]["PUBMED_ID"] == "123"


def test_exact_trial_and_publication(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    monkeypatch.setattr(main, "get_product_client", lambda: FakeProductClient())
    client = TestClient(main.app)
    trial = client.get(
        "/trials/NCT00000001", headers={"X-API-Key": "correct-key"}
    )
    publication = client.get(
        "/publications/123", headers={"X-API-Key": "correct-key"}
    )
    assert trial.status_code == 200
    assert publication.status_code == 200


def test_product_routes_reject_bad_identifiers(monkeypatch):
    monkeypatch.setenv("PFIZER_ANTIINF_API_KEY", "correct-key")
    client = TestClient(main.app)
    assert client.get(
        "/trials/not-an-nct", headers={"X-API-Key": "correct-key"}
    ).status_code == 422
    assert client.get(
        "/publications/not-a-pmid", headers={"X-API-Key": "correct-key"}
    ).status_code == 422
