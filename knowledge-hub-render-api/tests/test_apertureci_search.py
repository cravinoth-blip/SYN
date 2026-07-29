from __future__ import annotations

import pytest

from apertureci_search import (
    ALLOWED_SOURCES,
    ApertureCISearchClient,
    DEFAULT_SOURCES,
    query_terms,
    validate_scope_query,
)


def test_query_terms_are_bounded_and_remove_stop_words():
    assert query_terms(
        "What is the evidence for asundexian in ischemic stroke and atrial fibrillation?"
    ) == [
        "evidence",
        "asundexian",
        "ischemic",
        "stroke",
        "atrial",
        "fibrillation",
    ]


def test_apertureci_sources_are_fixed():
    assert ALLOWED_SOURCES == (
        "dexi",
        "publications",
        "clinical_trials",
        "competitor_maps",
        "trial_comparisons",
        "knowledge",
        "news",
        "congresses",
        "competitor_analysis",
        "schema",
    )


def test_every_schema_data_adapter_is_fixed_in_code():
    assert hasattr(ApertureCISearchClient, "_search_news")
    assert hasattr(ApertureCISearchClient, "_search_congresses")
    assert hasattr(ApertureCISearchClient, "_search_competitor_analysis")
    assert hasattr(ApertureCISearchClient, "_search_schema")


def test_client_rejects_an_arbitrary_source_before_connecting():
    client = ApertureCISearchClient(settings=None)
    with pytest.raises(ValueError, match="Unsupported APERTURECI source"):
        client.search(
            source="arbitrary_table",
            query="asundexian",
            limit=4,
        )


def test_all_source_caps_the_combined_response(monkeypatch):
    class Connection:
        def close(self):
            return None

    client = ApertureCISearchClient(settings=None)
    monkeypatch.setattr(client, "_connect", lambda: Connection())

    for selected_source in DEFAULT_SOURCES:
        monkeypatch.setattr(
            client,
            f"_search_{selected_source}",
            lambda connection, *, query, limit, context_id, source=selected_source: [
                {"SOURCE_TYPE": source, "RECORD_ID": f"{source}-{index}"}
                for index in range(limit)
            ],
        )

    results, errors, _ = client.search(
        source="all",
        query="ASUNDEXIAN versus MILVEXIAN",
        limit=4,
    )

    assert errors == []
    assert len(results) == 4
    assert [row["SOURCE_TYPE"] for row in results] == list(DEFAULT_SOURCES[:4])


def test_scope_accepts_primary_asset_and_competitor_aliases():
    assert validate_scope_query("Compare ASUNDEXIAN efficacy") == (
        "Compare ASUNDEXIAN efficacy"
    )
    assert validate_scope_query("BMS-986177 trial evidence") == (
        "BMS-986177 trial evidence"
    )


def test_scope_rejects_unrelated_asset_query():
    with pytest.raises(ValueError, match="only supports ASUNDEXIAN and MILVEXIAN"):
        validate_scope_query("Compare apixaban with rivaroxaban")
