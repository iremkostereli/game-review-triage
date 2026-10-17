"""Tests for annotator corrections to the golden set.

The corrections mechanism has to be strict: it edits the answer key everything
else is measured against, and it is driven by a queue selected from the system's
own output. So a correction must name the label it replaces, carry a reason, and
produce a label the taxonomy accepts, or it is refused.
"""

from __future__ import annotations

import pytest

from triage import corrections
from triage.jsonl_io import write_jsonl


GOLD_ROWS = [
    {"reviewId": "a", "game": "Clash of Clans", "score": 2,
     "categories": ["difficulty_balance"], "severity": "medium", "has_jargon": True},
    {"reviewId": "b", "game": "Candy Crush Saga", "score": 5,
     "categories": ["no_issue"], "severity": None, "has_jargon": False},
]


def write(tmp_path, rows):
    path = tmp_path / "corrections.jsonl"
    write_jsonl(path, rows)
    return path


def test_missing_file_means_no_corrections(tmp_path):
    assert corrections.load_corrections(tmp_path / "nope.jsonl") == []


def test_keep_entries_change_nothing(tmp_path):
    path = write(tmp_path, [{
        "reviewId": "a", "action": "keep",
        "old_categories": ["difficulty_balance"], "old_severity": "medium",
        "new_categories": ["content_ux"], "new_severity": "low",
        "reason": "ignored because the action is keep",
    }])
    rows, applied = corrections.apply_to_rows(GOLD_ROWS, corrections.load_corrections(path))
    assert applied == []
    assert rows[0]["categories"] == ["difficulty_balance"]


def test_a_change_is_applied_without_touching_the_original_rows(tmp_path):
    path = write(tmp_path, [{
        "reviewId": "a", "action": "change",
        "old_categories": ["difficulty_balance"], "old_severity": "medium",
        "new_categories": ["content_ux"], "new_severity": "low",
        "reason": "re-read the guide: this is a feature request",
    }])
    rows, applied = corrections.apply_to_rows(GOLD_ROWS, corrections.load_corrections(path))

    assert len(applied) == 1
    assert rows[0]["categories"] == ["content_ux"]
    assert rows[0]["severity"] == "low"
    assert rows[0]["corrected"] is True
    assert "feature request" in rows[0]["correction_reason"]
    # The input rows must not have been mutated in place.
    assert GOLD_ROWS[0]["categories"] == ["difficulty_balance"]


def test_a_change_needs_a_reason(tmp_path):
    path = write(tmp_path, [{
        "reviewId": "a", "action": "change",
        "old_categories": ["difficulty_balance"], "old_severity": "medium",
        "new_categories": ["content_ux"], "new_severity": "low",
        "reason": "",
    }])
    with pytest.raises(corrections.CorrectionError, match="needs a reason"):
        corrections.apply_to_rows(GOLD_ROWS, corrections.load_corrections(path))


def test_a_stale_correction_is_refused(tmp_path):
    """If the label moved since the correction was written, do not apply it blindly."""
    path = write(tmp_path, [{
        "reviewId": "a", "action": "change",
        "old_categories": ["ads"], "old_severity": "low",
        "new_categories": ["content_ux"], "new_severity": "low",
        "reason": "written against a label that is no longer there",
    }])
    with pytest.raises(corrections.CorrectionError, match="re-check it"):
        corrections.apply_to_rows(GOLD_ROWS, corrections.load_corrections(path))


def test_a_new_label_must_satisfy_the_taxonomy(tmp_path):
    path = write(tmp_path, [{
        "reviewId": "b", "action": "change",
        "old_categories": ["no_issue"], "old_severity": None,
        "new_categories": ["no_issue", "ads"], "new_severity": "low",
        "reason": "no_issue is exclusive, so this must be refused",
    }])
    with pytest.raises(corrections.CorrectionError, match="cannot be combined"):
        corrections.apply_to_rows(GOLD_ROWS, corrections.load_corrections(path))


def test_an_unknown_review_is_refused(tmp_path):
    path = write(tmp_path, [{
        "reviewId": "zzz", "action": "change",
        "old_categories": [], "old_severity": None,
        "new_categories": ["ads"], "new_severity": "low", "reason": "typo in the id",
    }])
    with pytest.raises(corrections.CorrectionError, match="not in the golden set"):
        corrections.apply_to_rows(GOLD_ROWS, corrections.load_corrections(path))


def test_duplicate_corrections_are_refused(tmp_path):
    path = write(tmp_path, [
        {"reviewId": "a", "action": "keep", "old_categories": ["difficulty_balance"]},
        {"reviewId": "a", "action": "keep", "old_categories": ["difficulty_balance"]},
    ])
    with pytest.raises(corrections.CorrectionError, match="duplicate correction"):
        corrections.load_corrections(path)


def test_unknown_action_is_refused(tmp_path):
    path = write(tmp_path, [{"reviewId": "a", "action": "maybe"}])
    with pytest.raises(corrections.CorrectionError, match="action must be one of"):
        corrections.load_corrections(path)


def test_scaffold_starts_as_a_no_op(tmp_path):
    """The generated file must change nothing until a human edits it."""
    candidates = [{
        "reviewId": "a",
        "gold_categories": ["difficulty_balance"],
        "gold_severity": "medium",
        "model_categories": ["content_ux"],
        "model_severity": "low",
    }]
    path = tmp_path / "scaffold.jsonl"
    assert corrections.write_scaffold(path, candidates) == 1

    rows, applied = corrections.apply_to_rows(GOLD_ROWS, corrections.load_corrections(path))
    assert applied == []
    assert rows[0]["categories"] == ["difficulty_balance"]


def test_scaffold_records_what_the_model_said_for_reference(tmp_path):
    candidates = [{
        "reviewId": "a",
        "gold_categories": ["difficulty_balance"],
        "gold_severity": "medium",
        "model_categories": ["content_ux"],
        "model_severity": "low",
    }]
    path = tmp_path / "scaffold.jsonl"
    corrections.write_scaffold(path, candidates)

    from triage.jsonl_io import read_jsonl

    row = read_jsonl(path)[0]
    assert row["action"] == "keep"
    assert row["model_said_categories"] == ["content_ux"]
    assert row["new_categories"] == ["difficulty_balance"], "starts equal to the old label"
