"""Tests for the dev/golden split.

The synthetic tests run anywhere. The tests that need the real corpus skip
themselves when data/raw is absent, so `pytest` stays green on a fresh clone.
"""

from __future__ import annotations

import pytest

from triage import paths, sampling
from triage.jsonl_io import read_json, read_jsonl

# --------------------------------------------------------------------------
# Synthetic: determinism and stratum logic, no dataset required
# --------------------------------------------------------------------------


def make_review(review_id: str, **overrides):
    review = {
        "reviewId": review_id,
        "game": "Clash of Clans",
        "content": "x " * 20,
        "score": 3,
        "words": 20,
        "looks_english": True,
        "tier1_jargon": False,
        "tier2_jargon": False,
        "complaint_cue": False,
    }
    review.update(overrides)
    return review


def build_pool(tier1: int, tier2: int, plain: int):
    reviews = []
    for index in range(tier1):
        reviews.append(make_review(f"t1-{index}", tier1_jargon=True))
    for index in range(tier2):
        reviews.append(make_review(f"t2-{index}", tier2_jargon=True))
    for index in range(plain):
        reviews.append(make_review(f"pl-{index}"))
    return reviews


def test_selection_key_is_stable_across_runs():
    assert sampling.selection_key("abc") == sampling.selection_key("abc")
    assert sampling.selection_key("abc") != sampling.selection_key("abd")


def test_sampling_is_independent_of_input_order():
    pool = build_pool(tier1=80, tier2=80, plain=200)
    first = sampling.sample_game("Clash of Clans", pool)
    second = sampling.sample_game("Clash of Clans", list(reversed(pool)))
    assert first.selected == second.selected


def test_sampling_hits_targets_when_supply_is_sufficient():
    pool = build_pool(tier1=80, tier2=80, plain=200)
    drawn = sampling.sample_game("Clash of Clans", pool)
    for stratum, target in sampling.TARGETS["Clash of Clans"].items():
        assert len(drawn.selected[stratum]) == target
    assert drawn.shortfalls == {}
    assert drawn.total == sum(sampling.TARGETS["Clash of Clans"].values())


def test_strata_never_overlap():
    pool = build_pool(tier1=80, tier2=80, plain=200)
    drawn = sampling.sample_game("Clash of Clans", pool)
    all_ids = [rid for ids in drawn.selected.values() for rid in ids]
    assert len(all_ids) == len(set(all_ids))


def test_shortfall_rolls_forward_and_total_is_preserved():
    """With only 5 tier1 reviews the total per game must still be 100."""
    pool = build_pool(tier1=5, tier2=200, plain=200)
    drawn = sampling.sample_game("Clash of Clans", pool)
    assert len(drawn.selected["tier1"]) == 5
    assert drawn.shortfalls["tier1"] == 31
    assert drawn.total == sum(sampling.TARGETS["Clash of Clans"].values())


def test_ineligible_reviews_are_never_selected():
    short = [make_review(f"short-{i}", words=4) for i in range(50)]
    non_english = [make_review(f"tr-{i}", looks_english=False) for i in range(50)]
    drawn = sampling.sample_game("Clash of Clans", short + non_english)
    assert drawn.total == 0
    assert drawn.eligible == 0


def test_high_star_complaint_counts_as_enriched():
    """A 5-star review with a complaint cue belongs to the enriched slice.

    This pool has no tier1 jargon at all, so the tier1 target rolls forward into
    enriched_other: 30 + 20 = 50. The game total is still preserved.
    """
    targets = sampling.TARGETS["Candy Crush Saga"]
    pool = [make_review(f"hs-{i}", score=5, complaint_cue=True) for i in range(200)]
    drawn = sampling.sample_game("Candy Crush Saga", pool)

    assert drawn.selected["tier1"] == []
    assert drawn.shortfalls["tier1"] == targets["tier1"]
    assert len(drawn.selected["enriched_other"]) == targets["enriched_other"] + targets["tier1"]
    assert drawn.total == sum(targets.values())


def test_golden_hash_ignores_ordering():
    assert sampling.golden_set_hash(["b", "a"]) == sampling.golden_set_hash(["a", "b"])


# --------------------------------------------------------------------------
# Real corpus: only runs when the split has been prepared
# --------------------------------------------------------------------------

needs_corpus = pytest.mark.skipif(
    not paths.REVIEWS_JSONL.exists(),
    reason="run scripts/prepare_data.py first (needs data/raw)",
)


@pytest.fixture(scope="module")
def corpus():
    return read_jsonl(paths.REVIEWS_JSONL)


@pytest.fixture(scope="module")
def manifest():
    return read_json(paths.SPLIT_MANIFEST)


@needs_corpus
def test_golden_and_dev_are_disjoint(corpus):
    golden = {r["reviewId"] for r in corpus if r["split"] == "golden"}
    dev = {r["reviewId"] for r in corpus if r["split"] == "dev"}
    assert golden & dev == set()
    assert len(golden) + len(dev) == len(corpus)


@needs_corpus
def test_manifest_matches_corpus(corpus, manifest):
    golden = sorted(r["reviewId"] for r in corpus if r["split"] == "golden")
    assert len(golden) == manifest["golden_total"] == 180
    assert sampling.golden_set_hash(golden) == manifest["golden_set_sha256"]


@needs_corpus
def test_every_golden_review_is_eligible(corpus):
    for review in corpus:
        if review["split"] == "golden":
            assert review["words"] >= sampling.MIN_WORDS
            assert review["looks_english"]


@needs_corpus
def test_no_duplicate_content_across_splits(corpus):
    seen: dict[tuple[str, str], str] = {}
    for review in corpus:
        key = (review["game"], " ".join(review["content"].lower().split()))
        assert key not in seen, f"duplicate content survived: {review['reviewId']}"
        seen[key] = review["reviewId"]


@needs_corpus
def test_golden_pool_matches_split(corpus):
    pool = read_jsonl(paths.GOLDEN_DIR / "golden_pool.jsonl")
    golden = {r["reviewId"] for r in corpus if r["split"] == "golden"}
    assert {r["reviewId"] for r in pool} == golden
    # The annotator must not see which stratum a review came from.
    for record in pool:
        assert "stratum" not in record and "slice" not in record


@needs_corpus
def test_dev_split_retains_jargon_for_pack_mining(corpus, manifest):
    """Half the strict-jargon reviews must stay outside the golden set.

    This is the constraint that made the budget work: packs are mined from the
    dev split, so the dev split has to keep real jargon in it.
    """
    for game in paths.EVAL_GAMES:
        dev_jargon = sum(
            1 for r in corpus
            if r["game"] == game and r["split"] == "dev" and r["tier1_jargon"]
        )
        assert dev_jargon >= 20, f"{game} left only {dev_jargon} jargon reviews in dev"
