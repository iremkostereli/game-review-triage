"""Tests for offline scoring.

The expected numbers here are worked out by hand from tiny fixtures, so a change
in the metric code shows up as a failing test rather than as a quietly different
headline figure.
"""

from __future__ import annotations

import json

import pytest

from triage import scoring
from triage.jsonl_io import write_json, write_jsonl

CATEGORIES = ("stability_performance", "monetization", "ads", "other_issue", "no_issue")


def gold_review(review_id, categories, severity, has_jargon=False, score=3,
                game="Clash of Clans", slice_name="enriched"):
    return scoring.GoldReview(
        review_id=review_id,
        game=game,
        score=score,
        categories=frozenset(categories),
        severity=severity,
        has_jargon=has_jargon,
        slice_name=slice_name,
    )


def prediction(review_id, categories, severity, has_jargon=False):
    return scoring.Prediction(
        review_id=review_id,
        categories=frozenset(categories),
        severity=severity,
        has_jargon=has_jargon,
    )


# --------------------------------------------------------------------------
# Metric arithmetic, checked by hand
# --------------------------------------------------------------------------


def test_perfect_predictions_score_one():
    pairs = [
        (gold_review("a", ["ads"], "low"), prediction("a", ["ads"], "low")),
        (gold_review("b", ["no_issue"], None), prediction("b", ["no_issue"], None)),
    ]
    scored = scoring.score_pairs(pairs, CATEGORIES)
    assert scored["category_micro"]["f1"] == 1.0
    assert scored["exact_set_match"] == 1.0
    assert scored["severity"]["accuracy"] == 1.0
    assert scored["issue_detection"]["f1"] == 1.0


def test_micro_f1_counts_labels_not_reviews():
    """One review with two gold labels, one of which was missed.

    tp=1 (monetization), fn=1 (ads), fp=1 (stability_performance).
    precision = recall = 1/2, so f1 = 0.5.
    """
    pairs = [
        (
            gold_review("a", ["monetization", "ads"], "medium"),
            prediction("a", ["monetization", "stability_performance"], "medium"),
        )
    ]
    scored = scoring.score_pairs(pairs, CATEGORIES)
    assert scored["category_micro"] == {"precision": 0.5, "recall": 0.5, "f1": 0.5}
    assert scored["exact_set_match"] == 0.0


def test_macro_f1_ignores_categories_absent_from_the_gold():
    """A category with no gold examples must not drag the average around."""
    pairs = [
        (gold_review("a", ["ads"], "low"), prediction("a", ["ads"], "low")),
        (gold_review("b", ["ads"], "low"), prediction("b", ["ads"], "low")),
    ]
    scored = scoring.score_pairs(pairs, CATEGORIES)
    # Only `ads` has support, and it is perfect.
    assert scored["category_macro_f1"] == 1.0
    assert set(scored["per_category_support"]) == {"ads"}


def test_severity_within_one_is_more_forgiving_than_exact():
    pairs = [
        (gold_review("a", ["ads"], "high"), prediction("a", ["ads"], "medium")),
        (gold_review("b", ["ads"], "low"), prediction("b", ["ads"], "high")),
    ]
    scored = scoring.score_pairs(pairs, CATEGORIES)
    assert scored["severity"]["accuracy"] == 0.0
    # high vs medium is one step; low vs high is two.
    assert scored["severity"]["within_one"] == 0.5


def test_severity_is_only_scored_where_the_annotator_rated_one():
    pairs = [
        (gold_review("a", ["no_issue"], None), prediction("a", ["no_issue"], None)),
        (gold_review("b", ["ads"], "low"), prediction("b", ["ads"], "low")),
    ]
    scored = scoring.score_pairs(pairs, CATEGORIES)
    assert scored["severity"]["n"] == 1
    assert scored["severity"]["accuracy"] == 1.0


def test_high_star_issue_recall_measures_the_star_trap():
    """The headline claim: real issues hiding behind 4-5 star ratings."""
    pairs = [
        # 5 stars, a real issue, correctly caught
        (gold_review("a", ["ads"], "low", score=5), prediction("a", ["ads"], "low")),
        # 4 stars, a real issue, wrongly called praise
        (gold_review("b", ["monetization"], "medium", score=4),
         prediction("b", ["no_issue"], None)),
        # 5 stars, genuinely praise: not part of this metric
        (gold_review("c", ["no_issue"], None, score=5), prediction("c", ["no_issue"], None)),
        # 1 star: not part of this metric either
        (gold_review("d", ["ads"], "low", score=1), prediction("d", ["ads"], "low")),
    ]
    scored = scoring.score_pairs(pairs, CATEGORIES)
    assert scored["high_star_issue_recall"] == {"n": 2, "recall": 0.5}


def test_jargon_flag_agreement_compares_against_the_hand_flag():
    pairs = [
        (gold_review("a", ["ads"], "low", has_jargon=True),
         prediction("a", ["ads"], "low", has_jargon=True)),
        (gold_review("b", ["ads"], "low", has_jargon=False),
         prediction("b", ["ads"], "low", has_jargon=True)),
    ]
    assert scoring.score_pairs(pairs, CATEGORIES)["jargon_flag_agreement"] == 0.5


def test_empty_pairs_do_not_crash():
    assert scoring.score_pairs([], CATEGORIES) == {"n": 0}


# --------------------------------------------------------------------------
# Slices
# --------------------------------------------------------------------------


def test_slices_split_on_the_hand_flag_and_the_sampling_slice():
    gold = {
        "a": gold_review("a", ["ads"], "low", has_jargon=True, slice_name="enriched"),
        "b": gold_review("b", ["ads"], "low", has_jargon=False, slice_name="random"),
    }
    slices = scoring.slice_definitions(["Clash of Clans"])
    assert [rid for rid in gold if slices["jargon"](gold[rid])] == ["a"]
    assert [rid for rid in gold if slices["no_jargon"](gold[rid])] == ["b"]
    assert [rid for rid in gold if slices["slice_random"](gold[rid])] == ["b"]
    assert [rid for rid in gold if slices["slice_enriched"](gold[rid])] == ["a"]
    assert [rid for rid in gold if slices["game_Clash of Clans"](gold[rid])] == ["a", "b"]


# --------------------------------------------------------------------------
# Bootstrap
# --------------------------------------------------------------------------


def make_run(mode, repeat, preds):
    return scoring.Run(
        pack_mode=mode, repeat=repeat, predictions=preds, batches=("b",), games=("g",)
    )


def test_bootstrap_reports_zero_delta_when_conditions_agree():
    gold = {f"r{i}": gold_review(f"r{i}", ["ads"], "low") for i in range(10)}
    preds = {rid: prediction(rid, ["ads"], "low") for rid in gold}
    result = scoring.paired_bootstrap_all(
        gold, [make_run("off", 1, preds)], [make_run("on", 1, dict(preds))],
        keep=lambda g: True, resamples=50,
    )
    entry = result["category_micro.f1"]
    assert entry["delta"] == 0.0
    assert entry["ci_low"] == entry["ci_high"] == 0.0
    assert entry["significant"] is False


def test_bootstrap_detects_a_consistent_improvement():
    """ON is right everywhere, OFF is wrong everywhere: the interval must exclude zero."""
    gold = {f"r{i}": gold_review(f"r{i}", ["ads"], "low") for i in range(20)}
    off = {rid: prediction(rid, ["monetization"], "low") for rid in gold}
    on = {rid: prediction(rid, ["ads"], "low") for rid in gold}
    result = scoring.paired_bootstrap_all(
        gold, [make_run("off", 1, off)], [make_run("on", 1, on)],
        keep=lambda g: True, resamples=200,
    )
    entry = result["category_micro.f1"]
    assert entry["off"] == 0.0 and entry["on"] == 1.0
    assert entry["delta"] == 1.0
    assert entry["ci_low"] > 0
    assert entry["significant"] is True


def test_bootstrap_is_reproducible():
    gold = {f"r{i}": gold_review(f"r{i}", ["ads"], "low") for i in range(15)}
    off = {rid: prediction(rid, ["ads"] if i % 2 else ["ads", "monetization"], "low")
           for i, rid in enumerate(gold)}
    on = {rid: prediction(rid, ["ads"], "low") for rid in gold}
    runs = ([make_run("off", 1, off)], [make_run("on", 1, on)])
    first = scoring.paired_bootstrap_all(gold, *runs, keep=lambda g: True, resamples=100)
    second = scoring.paired_bootstrap_all(gold, *runs, keep=lambda g: True, resamples=100)
    assert first == second


def test_bootstrap_only_uses_reviews_present_in_every_run():
    """A review missing from one run cannot be part of a paired comparison."""
    gold = {f"r{i}": gold_review(f"r{i}", ["ads"], "low") for i in range(5)}
    off = {rid: prediction(rid, ["ads"], "low") for rid in gold}
    on = {rid: prediction(rid, ["ads"], "low") for rid in list(gold)[:3]}
    result = scoring.paired_bootstrap_all(
        gold, [make_run("off", 1, off)], [make_run("on", 1, on)],
        keep=lambda g: True, resamples=20,
    )
    assert result["category_micro.f1"]["n"] == 3


def test_aggregate_repeats_reports_spread():
    scored = [
        {"category_micro": {"f1": 0.8}},
        {"category_micro": {"f1": 0.6}},
    ]
    agg = scoring.aggregate_repeats(scored, "category_micro.f1")
    assert agg["runs"] == 2
    assert agg["mean"] == 0.7
    assert agg["stdev"] > 0
    assert agg["values"] == [0.8, 0.6]


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def test_load_gold_drops_withheld_reviews_and_attaches_slices(tmp_path):
    golden = tmp_path / "golden_set.jsonl"
    write_jsonl(golden, [
        {"reviewId": "a", "game": "Clash of Clans", "score": 5, "categories": ["no_issue"],
         "severity": None, "has_jargon": False, "unclear": False, "note": ""},
        {"reviewId": "b", "game": "Clash of Clans", "score": 1, "categories": [],
         "severity": None, "has_jargon": False, "unclear": True, "note": ""},
    ])
    slices = tmp_path / "slices.json"
    write_json(slices, {"slices": {"a": "random", "b": "enriched"}})
    excluded = tmp_path / "excluded.json"
    write_json(excluded, {"excluded": [{"reviewId": "b", "reason": "unclear"}]})

    gold = scoring.load_gold(golden, slices, excluded)
    assert set(gold) == {"a"}
    assert gold["a"].slice_name == "random"


def test_load_runs_merges_batches_and_games_per_repeat(tmp_path):
    for name, game, mode, results in [
        ("g1-off-r1-b1", "Game One", "off", ["a", "b"]),
        ("g1-off-r1-b2", "Game One", "off", ["c"]),
        ("g2-off-r1-b1", "Game Two", "off", ["d"]),
        ("g1-on-r1-b1", "Game One", "on", ["a"]),
    ]:
        d = tmp_path / name
        d.mkdir()
        write_json(d / "meta.json", {
            "run_id": name, "game": game, "pack_mode": mode, "repeat": 1,
            "status": "ok", "result_count": len(results),
        })
        write_json(d / "output.json", {"results": [
            {"reviewId": r, "categories": ["ads"], "severity": "low", "has_jargon": False}
            for r in results
        ]})

    runs = {r.pack_mode: r for r in scoring.load_runs(tmp_path)}
    assert set(runs["off"].predictions) == {"a", "b", "c", "d"}
    assert runs["off"].games == ("Game One", "Game Two")
    assert len(runs["off"].batches) == 3
    assert set(runs["on"].predictions) == {"a"}


def test_load_runs_ignores_batches_that_were_not_complete(tmp_path):
    d = tmp_path / "g1-off-r1-b1"
    d.mkdir()
    write_json(d / "meta.json", {
        "run_id": "g1-off-r1-b1", "game": "G", "pack_mode": "off", "repeat": 1,
        "status": "rejected", "result_count": 1,
    })
    write_json(d / "output.json", {"results": [
        {"reviewId": "a", "categories": ["ads"], "severity": "low", "has_jargon": False}
    ]})
    assert scoring.load_runs(tmp_path) == []
