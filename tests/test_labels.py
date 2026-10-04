"""Tests for label storage, validation and golden-set export."""

from __future__ import annotations

import pytest

from triage.labels import LabelStore, export_golden_set, normalize
from triage.taxonomy import LabelError


@pytest.fixture
def store(tmp_path):
    return LabelStore(tmp_path / "labels.partial.jsonl")


@pytest.fixture
def pool():
    return [
        {
            "reviewId": "r1",
            "game": "Clash of Clans",
            "content": "th14 war matchmaking is broken",
            "score": 2,
            "date": "2026-02-01 10:00:00",
            "appVersion": "1.0",
            "words": 5,
        },
        {
            "reviewId": "r2",
            "game": "Candy Crush Saga",
            "content": "best relaxing game",
            "score": 5,
            "date": "2026-02-02 10:00:00",
            "appVersion": None,
            "words": 3,
        },
    ]


def label(review_id, categories, severity, **extra):
    record = {
        "reviewId": review_id,
        "categories": categories,
        "severity": severity,
        "has_jargon": extra.get("has_jargon", False),
        "unclear": extra.get("unclear", False),
        "note": extra.get("note", ""),
    }
    return record


# --------------------------------------------------------------------------
# Normalisation and storage
# --------------------------------------------------------------------------


def test_normalize_sorts_categories_and_trims_note():
    record = normalize(
        {"reviewId": "r1", "categories": ["monetization", "ads"], "severity": "medium",
         "note": "  unsure  "}
    )
    assert record["categories"] == ["ads", "monetization"]
    assert record["note"] == "unsure"
    assert record["has_jargon"] is False
    assert record["unclear"] is False


def test_normalize_treats_empty_severity_as_none():
    assert normalize({"reviewId": "r", "categories": ["no_issue"], "severity": ""})["severity"] is None


def test_save_and_load_roundtrip(store):
    store.save(label("r1", ["ads"], "medium"))
    loaded = store.load()
    assert loaded["r1"]["categories"] == ["ads"]
    assert loaded["r1"]["labeled_at"]


def test_last_write_wins(store):
    """Changing your mind later must override the earlier answer."""
    store.save(label("r1", ["ads"], "low"))
    store.save(label("r1", ["monetization"], "high", note="changed my mind"))
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded["r1"]["categories"] == ["monetization"]
    assert loaded["r1"]["severity"] == "high"
    assert loaded["r1"]["note"] == "changed my mind"


def test_log_is_append_only(store):
    store.save(label("r1", ["ads"], "low"))
    store.save(label("r1", ["ads"], "high"))
    lines = store.path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2, "history should be preserved, not overwritten"


def test_load_is_empty_before_any_labeling(store):
    assert store.load() == {}


def test_invalid_labels_are_rejected_on_save(store):
    with pytest.raises(LabelError, match="cannot be combined"):
        store.save(label("r1", ["no_issue", "ads"], "low"))
    with pytest.raises(LabelError, match="severity is required"):
        store.save(label("r1", ["ads"], None))
    assert not store.path.exists(), "a rejected label must not be written"


def test_unclear_may_have_no_categories(store):
    """The annotator must be able to say 'I cannot label this' without guessing."""
    store.save(label("r1", [], None, unclear=True, note="not English"))
    assert store.load()["r1"]["unclear"] is True


def test_counts_tracks_progress(store, pool):
    ids = [r["reviewId"] for r in pool]
    assert store.counts(ids) == {"total": 2, "labeled": 0, "remaining": 2, "noted": 0, "unclear": 0}
    store.save(label("r1", ["ads"], "low", note="check later"))
    assert store.counts(ids) == {"total": 2, "labeled": 1, "remaining": 1, "noted": 1, "unclear": 0}


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------


def test_export_refuses_an_incomplete_golden_set(store, pool, tmp_path):
    store.save(label("r1", ["difficulty_balance"], "medium", has_jargon=True))
    with pytest.raises(LabelError, match="not labeled yet"):
        export_golden_set(pool, store, tmp_path / "golden.jsonl")
    assert not (tmp_path / "golden.jsonl").exists(), "must not write a partial answer key"


def test_export_writes_labels_joined_to_review_text(store, pool, tmp_path):
    store.save(label("r1", ["difficulty_balance"], "medium", has_jargon=True, note="jargon heavy"))
    store.save(label("r2", ["no_issue"], None))
    out = tmp_path / "golden.jsonl"

    result = export_golden_set(pool, store, out)
    assert result["written"] == 2
    assert result["noted"] == 1

    from triage.jsonl_io import read_jsonl

    rows = {row["reviewId"]: row for row in read_jsonl(out)}
    # Review text travels with the labels so scoring works without the raw CSV.
    assert rows["r1"]["content"] == "th14 war matchmaking is broken"
    assert rows["r1"]["game"] == "Clash of Clans"
    assert rows["r1"]["score"] == 2
    assert rows["r1"]["categories"] == ["difficulty_balance"]
    assert rows["r1"]["has_jargon"] is True
    assert rows["r2"]["severity"] is None


def test_export_can_be_partial_when_explicitly_allowed(store, pool, tmp_path):
    store.save(label("r1", ["ads"], "low"))
    out = tmp_path / "golden.jsonl"
    result = export_golden_set(pool, store, out, require_complete=False)
    assert result["written"] == 1
    assert result["unlabeled"] == 1


def test_export_does_not_leak_sampling_hints(store, pool, tmp_path):
    """Stratum and slice must not reach the answer key.

    They describe why a review was offered for labeling, which is a property of
    the sampling heuristic rather than of the review, and keeping them out stops
    anyone scoring the jargon slice by the heuristic instead of the hand flag.
    """
    store.save(label("r1", ["ads"], "low"))
    store.save(label("r2", ["no_issue"], None))
    out = tmp_path / "golden.jsonl"
    export_golden_set(pool, store, out)

    from triage.jsonl_io import read_jsonl

    for row in read_jsonl(out):
        assert "stratum" not in row
        assert "slice" not in row
        assert "tier1_jargon" not in row
