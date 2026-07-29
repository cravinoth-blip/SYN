from __future__ import annotations

import pytest

from apertureci_search import (
    ALLOWED_SOURCES,
    ApertureCISearchClient,
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
    )


def test_client_rejects_an_arbitrary_source_before_connecting():
    client = ApertureCISearchClient(settings=None)
    with pytest.raises(ValueError, match="Unsupported APERTURECI source"):
        client.search(
            source="arbitrary_table",
            query="asundexian",
            limit=4,
        )


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
