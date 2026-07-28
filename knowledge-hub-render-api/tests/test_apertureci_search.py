from __future__ import annotations

import pytest

from apertureci_search import ALLOWED_SOURCES, ApertureCISearchClient, query_terms


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
