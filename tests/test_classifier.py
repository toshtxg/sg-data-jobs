"""Tests for pipeline.classifier pure transforms and LLM-response parsing.

The real OpenAI client is never called: classify_batch is exercised against a
fake client whose create() returns a canned JSON string. The row-building and
enum-enforcement helpers are pure and tested directly.
"""

import json

import pytest

from pipeline import classifier
from pipeline.classifier import (
    _build_classification_row,
    _enforce_enums,
    classify_batch,
)


# ---------------------------------------------------------------------------
# _enforce_enums
# ---------------------------------------------------------------------------

def test_enforce_enums_replaces_invalid_values_with_defaults():
    result = {
        "role_category": "Wizard",
        "seniority_level": "Overlord",
        "remote_hybrid_onsite": "Teleport",
    }
    out = _enforce_enums(result)
    assert out["role_category"] == "Other"
    assert out["seniority_level"] == "Mid"
    assert out["remote_hybrid_onsite"] == "Unknown"


def test_enforce_enums_preserves_valid_values():
    result = {
        "role_category": "ML Engineer",
        "seniority_level": "Senior",
        "remote_hybrid_onsite": "Hybrid",
    }
    out = _enforce_enums(result)
    assert out["role_category"] == "ML Engineer"
    assert out["seniority_level"] == "Senior"
    assert out["remote_hybrid_onsite"] == "Hybrid"


def test_enforce_enums_missing_keys_become_defaults():
    out = _enforce_enums({})
    assert out["role_category"] == "Other"
    assert out["seniority_level"] == "Mid"
    assert out["remote_hybrid_onsite"] == "Unknown"


# ---------------------------------------------------------------------------
# _build_classification_row
# ---------------------------------------------------------------------------

def test_build_row_maps_and_normalizes_skills():
    listing = {"id": 42, "title": "Data Scientist"}
    result = {
        "role_category": "Data Scientist",
        "seniority_level": "Senior",
        "technical_skills": ["python3", "Python", "sklearn"],
        "soft_skills": ["communication"],
        "domain_knowledge": ["Finance"],
        "requires_ai_ml": True,
        "remote_hybrid_onsite": "Remote",
        "industry": "Banking",
    }
    row = _build_classification_row(listing, result)

    assert row["listing_id"] == 42
    assert row["role_category"] == "Data Scientist"
    assert row["seniority_level"] == "Senior"
    # Skills normalized + deduped: python3/Python -> Python, sklearn -> Scikit-learn
    assert row["technical_skills"] == ["Python", "Scikit-learn"]
    assert row["soft_skills"] == ["Communication"]
    assert row["domain_knowledge"] == ["Finance"]
    assert row["requires_ai_ml"] is True
    assert row["remote_hybrid_onsite"] == "Remote"
    assert row["industry"] == "Banking"
    assert row["model_used"] == classifier.CLASSIFIER_MODEL


def test_build_row_applies_defaults_for_missing_fields():
    listing = {"id": 7}
    row = _build_classification_row(listing, {})
    assert row["listing_id"] == 7
    assert row["role_category"] == "Other"
    assert row["seniority_level"] == "Mid"
    assert row["technical_skills"] == []
    assert row["soft_skills"] == []
    assert row["domain_knowledge"] == []
    assert row["requires_ai_ml"] is False
    assert row["remote_hybrid_onsite"] == "Unknown"
    assert row["industry"] == "Technology"


# ---------------------------------------------------------------------------
# classify_batch — LLM response parsing / index reconciliation
# ---------------------------------------------------------------------------

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeClient:
    """Stands in for the OpenAI client; returns a preset JSON string."""

    def __init__(self, content):
        self._content = content
        self.calls = 0

        class _Completions:
            def create(inner_self, **_kwargs):
                self.calls += 1
                return _FakeCompletion(self._content)

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


@pytest.fixture
def fake_client(monkeypatch):
    def _install(payload):
        content = payload if isinstance(payload, str) else json.dumps(payload)
        client = _FakeClient(content)
        monkeypatch.setattr(classifier, "client", client)
        return client

    return _install


def _listings(n):
    return [{"id": i, "title": f"Job {i}"} for i in range(n)]


def test_classify_batch_empty_returns_empty_without_calling_client(fake_client):
    client = fake_client({"results": []})
    assert classify_batch([]) == []
    assert client.calls == 0


def test_classify_batch_aligns_out_of_order_indexes(fake_client):
    fake_client({
        "results": [
            {"index": 2, "role_category": "Data Analyst"},
            {"index": 0, "role_category": "Data Scientist"},
            {"index": 1, "role_category": "ML Engineer"},
        ]
    })
    out = classify_batch(_listings(3))
    assert [r["role_category"] for r in out] == [
        "Data Scientist",
        "ML Engineer",
        "Data Analyst",
    ]
    # The reconciliation strips the routing "index" key from each result.
    assert all("index" not in r for r in out)


def test_classify_batch_missing_index_yields_none_in_slot(fake_client):
    fake_client({
        "results": [
            {"index": 0, "role_category": "Data Scientist"},
            {"index": 2, "role_category": "Data Analyst"},
        ]
    })
    out = classify_batch(_listings(3))
    assert out[0]["role_category"] == "Data Scientist"
    assert out[1] is None  # index 1 was never returned
    assert out[2]["role_category"] == "Data Analyst"


def test_classify_batch_ignores_duplicate_and_out_of_range_indexes(fake_client):
    fake_client({
        "results": [
            {"index": 0, "role_category": "First"},
            {"index": 0, "role_category": "DuplicateShouldBeIgnored"},
            {"index": 99, "role_category": "OutOfRangeIgnored"},
            {"index": -1, "role_category": "NegativeIgnored"},
            {"index": 1, "role_category": "Second"},
        ]
    })
    out = classify_batch(_listings(2))
    # First-wins for duplicate index 0; out-of-range and negative dropped.
    assert out[0]["role_category"] == "First"
    assert out[1]["role_category"] == "Second"


def test_classify_batch_non_dict_items_are_skipped(fake_client):
    fake_client({
        "results": [
            "not a dict",
            {"index": 0, "role_category": "Data Engineer"},
            None,
        ]
    })
    out = classify_batch(_listings(1))
    assert out[0]["role_category"] == "Data Engineer"


def test_classify_batch_malformed_results_returns_all_none(fake_client):
    # "results" is not a list -> ValueError caught -> [None]*n returned.
    fake_client({"results": "oops"})
    out = classify_batch(_listings(3))
    assert out == [None, None, None]


def test_classify_batch_invalid_json_returns_all_none(fake_client):
    fake_client("this is not json{")
    out = classify_batch(_listings(2))
    assert out == [None, None]


# ---------------------------------------------------------------------------
# classify_unprocessed — concurrent waves and time budget
# ---------------------------------------------------------------------------

@pytest.fixture
def unprocessed_env(monkeypatch):
    """Stub the DB fetch/store and the per-batch classifier call."""
    stored: list[dict] = []
    classified_batches: list[list[int]] = []

    def _install(n_listings):
        listings = [
            {"id": i, "title": f"Job {i}", "posting_date": f"2026-01-{i + 1:02d}"}
            for i in range(n_listings)
        ]
        monkeypatch.setattr(
            classifier, "_fetch_unclassified_antijoin", lambda _c: list(listings)
        )

        def _store(_client, rows):
            stored.extend(rows)
            return len(rows)

        def _classify(batch):
            classified_batches.append([row["id"] for row in batch])
            return [{"role_category": "Data Analyst"} for _ in batch]

        monkeypatch.setattr(classifier, "_store_classification_rows", _store)
        monkeypatch.setattr(classifier, "_classify_chunk", _classify)
        monkeypatch.setattr(classifier, "REQUEST_DELAY_SECONDS", 0)
        return stored, classified_batches

    return _install


def test_classify_unprocessed_classifies_every_batch_concurrently(unprocessed_env):
    stored, batches = unprocessed_env(23)
    count = classifier.classify_unprocessed(None, batch_size=5, concurrency=3)
    assert count == 23
    assert sorted(row["listing_id"] for row in stored) == list(range(23))
    assert len(batches) == 5


def test_classify_unprocessed_stops_at_deadline(unprocessed_env):
    stored, batches = unprocessed_env(20)
    # Deadline already passed: nothing is started, run still returns cleanly.
    count = classifier.classify_unprocessed(
        None, batch_size=5, concurrency=2, deadline=0.0
    )
    assert count == 0
    assert stored == []
    assert batches == []


def test_classify_unprocessed_quota_error_raises_pipeline_error(
    unprocessed_env, monkeypatch
):
    unprocessed_env(10)

    class _QuotaError(classifier.APIError):
        def __init__(self):
            self.code = "insufficient_quota"

    def _raise(_batch):
        raise _QuotaError()

    monkeypatch.setattr(classifier, "_classify_chunk", _raise)
    with pytest.raises(classifier.ClassificationPipelineError):
        classifier.classify_unprocessed(None, batch_size=5, concurrency=2)
