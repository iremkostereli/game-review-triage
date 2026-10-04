"""Tests for the taxonomy and the label rules it enforces."""

from __future__ import annotations

import pytest

from triage import paths
from triage.jsonl_io import read_jsonl
from triage.taxonomy import (
    NO_ISSUE,
    OTHER_ISSUE,
    LabelError,
    load_taxonomy,
    validate_label_record,
    validate_labels,
)


@pytest.fixture(scope="module")
def taxonomy():
    return load_taxonomy()


def test_taxonomy_loads_and_has_the_agreed_shape(taxonomy):
    # Six issue categories, plus other_issue and no_issue.
    assert len(taxonomy.categories) == 8
    assert NO_ISSUE in taxonomy.category_ids
    assert OTHER_ISSUE in taxonomy.category_ids
    assert set(taxonomy.severity_levels) == {"low", "medium", "high"}


def test_every_category_is_documented(taxonomy):
    for category in taxonomy.categories:
        assert category.definition, f"{category.id} has no definition"
        assert category.examples, f"{category.id} has no examples"
        for example in category.examples:
            assert example.get("quote"), f"{category.id} example without a quote"
            assert example.get("why"), f"{category.id} example without a rationale"


def test_only_no_issue_is_exclusive(taxonomy):
    exclusive = [c.id for c in taxonomy.categories if c.exclusive]
    assert exclusive == [NO_ISSUE]


def test_every_category_has_severity_guidance(taxonomy):
    """Severity must not be a fixed property of a category.

    Each category states its typical level and what moves it, so the annotator
    and the skill apply the same reasoning instead of guessing.
    """
    for category in taxonomy.categories:
        guidance = category.severity_guidance
        assert guidance, f"{category.id} has no severity_guidance"
        assert guidance.get("typical"), f"{category.id} has no typical severity"
        if category.id == NO_ISSUE:
            continue
        movers = [key for key in guidance if key.startswith(("escalate", "de_escalate"))]
        assert len(movers) >= 2, f"{category.id} must state both escalation and de-escalation"
        for key in movers:
            assert guidance[key].get("reason"), f"{category.id}.{key} has no reason"


def test_boundary_cases_are_decided(taxonomy):
    """The four known overlaps must each have a rule and a worked example."""
    boundaries = taxonomy.boundaries
    assert boundaries.get("general_rule")

    case_ids = {case["id"] for case in boundaries["cases"]}
    assert {
        "crash_causing_loss",
        "paid_but_not_delivered",
        "ad_reward_not_granted",
        "difficulty_forcing_spending",
    } <= case_ids

    for case in boundaries["cases"]:
        assert case.get("question"), f"{case['id']} has no question"
        assert case.get("rule"), f"{case['id']} has no rule"
        worked = [case.get(key) for key in ("both_labels", "single_label", "three_labels")]
        assert any(worked), f"{case['id']} has no worked example"

    assert boundaries.get("keyword_traps"), "keyword traps teach that a word is not a category"


def test_boundary_examples_use_real_category_ids(taxonomy):
    """A boundary example that cites a renamed category would silently mislead."""
    valid = set(taxonomy.category_ids)
    nodes = list(taxonomy.boundaries.get("cases", [])) + list(
        taxonomy.boundaries.get("keyword_traps", [])
    )
    for node in nodes:
        candidates = [node] if "labels" in node else list(node.values())
        for candidate in candidates:
            if isinstance(candidate, dict) and "labels" in candidate:
                unknown = set(candidate["labels"]) - valid
                assert not unknown, f"boundary example cites unknown categories: {unknown}"


def test_note_flag_is_documented(taxonomy):
    """The labeling tool's optional note field is part of the agreed schema."""
    assert "note" in taxonomy.flags
    assert taxonomy.flags["note"].get("optional") is True


# --------------------------------------------------------------------------
# Label rules
# --------------------------------------------------------------------------


def test_valid_multi_label_is_accepted():
    validate_labels(["monetization", "ads"], "medium")


def test_no_issue_must_stand_alone():
    validate_labels([NO_ISSUE], None)
    with pytest.raises(LabelError, match="cannot be combined"):
        validate_labels([NO_ISSUE, "ads"], "low")


def test_no_issue_must_not_carry_severity():
    with pytest.raises(LabelError, match="severity must be empty"):
        validate_labels([NO_ISSUE], "low")


def test_other_issue_is_a_fallback_not_an_extra_tag():
    validate_labels([OTHER_ISSUE], "medium")
    with pytest.raises(LabelError, match="fallback"):
        validate_labels([OTHER_ISSUE, "ads"], "medium")


def test_issue_requires_severity():
    with pytest.raises(LabelError, match="severity is required"):
        validate_labels(["ads"], None)


def test_unknown_values_are_rejected():
    with pytest.raises(LabelError, match="unknown categories"):
        validate_labels(["not_a_category"], "low")
    with pytest.raises(LabelError, match="unknown severity"):
        validate_labels(["ads"], "catastrophic")


def test_empty_and_duplicate_selections_are_rejected():
    with pytest.raises(LabelError, match="at least one category"):
        validate_labels([], "low")
    with pytest.raises(LabelError, match="duplicate categories"):
        validate_labels(["ads", "ads"], "low")


def test_label_record_validation():
    validate_label_record(
        {"reviewId": "x", "categories": ["ads"], "severity": "medium", "has_jargon": False}
    )
    with pytest.raises(LabelError, match="missing 'has_jargon'"):
        validate_label_record({"reviewId": "x", "categories": ["ads"], "severity": "low"})
    with pytest.raises(LabelError, match="must be a boolean"):
        validate_label_record(
            {"reviewId": "x", "categories": ["ads"], "severity": "low", "has_jargon": "yes"}
        )


# --------------------------------------------------------------------------
# Provenance: the taxonomy was drafted from the dev split only
# --------------------------------------------------------------------------


@pytest.mark.skipif(
    not paths.REVIEWS_JSONL.exists(),
    reason="run scripts/prepare_data.py first (needs data/raw)",
)
def test_taxonomy_examples_never_cite_a_golden_review(taxonomy):
    """The taxonomy ships inside the skill prompt, so its examples must be dev-only.

    Citing a golden review here would put held-out text into the prompt for both
    the pack OFF and pack ON conditions, quietly contaminating the eval.
    """
    corpus = read_jsonl(paths.REVIEWS_JSONL)
    golden = {r["reviewId"] for r in corpus if r["split"] == "golden"}
    known = {r["reviewId"] for r in corpus}

    cited = taxonomy.example_review_ids()
    assert cited, "taxonomy cites no review ids"

    leaked = sorted(set(cited) & golden)
    assert not leaked, f"taxonomy examples cite golden reviews: {leaked}"

    unknown = sorted(set(cited) - known)
    assert not unknown, f"taxonomy cites review ids not in the corpus: {unknown}"
