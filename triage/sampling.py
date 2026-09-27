"""Deterministic stratified sampling of the golden set.

Two properties matter more than anything else here:

1. **Determinism.** Selection is driven by ``sha256(reviewId)`` rather than a
   random number generator, so the same input always yields byte-identical output
   on any machine, any Python version, with no seed to remember.

2. **Enough signal to measure.** Reviews in this corpus are tiny (median 3-5
   words) and overwhelmingly positive, so a uniform sample would be mostly
   one-word praise and the pack OFF/ON comparison would measure nothing. The
   golden set is therefore two labeled slices:

   - ``random``   - a uniform sample of *substantive* reviews, giving an honest
                    base rate (honest about being conditional on length).
   - ``enriched`` - over-samples jargon-bearing reviews and "high star rating but
                    actually complaining" reviews, where a jargon pack can
                    plausibly change the answer.

   Both slices are scored separately, so the README can show where the pack helps
   and where it does not.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Sequence

from triage import sampling_terms

# Minimum words for a review to be worth an annotator's time. Below this the
# text is almost always "good", "nice game", or an emoji.
MIN_WORDS = 12

#: Per-game golden-set targets. Clash gets a bigger enriched slice because it has
#: more jargon-bearing reviews to spare; the caps keep roughly half of each game's
#: strict-jargon reviews in the dev split, where the jargon packs are built from.
TARGETS: dict[str, dict[str, int]] = {
    "Clash of Clans": {"tier1": 36, "enriched_other": 34, "random": 30},
    "Candy Crush Saga": {"tier1": 20, "enriched_other": 30, "random": 30},
}

#: Slice each stratum belongs to, for reporting.
STRATUM_SLICE = {"tier1": "enriched", "enriched_other": "enriched", "random": "random"}


def selection_key(review_id: str) -> str:
    """Stable per-review sort key. Independent of platform and Python version."""
    return hashlib.sha256(review_id.encode("utf-8")).hexdigest()


@dataclass
class GameSampling:
    """What was actually drawn for one game, including any shortfalls."""

    game: str
    eligible: int = 0
    selected: dict[str, list[str]] = field(default_factory=dict)
    shortfalls: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(len(ids) for ids in self.selected.values())


def is_eligible(review: dict[str, Any]) -> bool:
    """Long enough and English enough to be worth hand-labeling."""
    return review["words"] >= MIN_WORDS and review["looks_english"]


def _stratum_of(review: dict[str, Any]) -> str | None:
    """Which enriched stratum a review belongs to, or None if neither.

    ``tier1`` is unambiguous game jargon. ``enriched_other`` is the weaker signal:
    domain vocabulary, or a high star rating paired with a complaint cue - the
    case that motivates not trusting star ratings.
    """
    if review["tier1_jargon"]:
        return "tier1"
    high_star_complaint = review["score"] >= 4 and review["complaint_cue"]
    if review["tier2_jargon"] or high_star_complaint:
        return "enriched_other"
    return None


def sample_game(game: str, reviews: Sequence[dict[str, Any]]) -> GameSampling:
    """Draw one game's golden set from its reviews.

    Strata are filled in order (tier1, enriched_other, random). If a stratum is
    short of its target the shortfall is recorded and rolls forward, so the total
    per game stays fixed even when jargon supply runs out.
    """
    targets = TARGETS[game]
    result = GameSampling(game=game)

    eligible = sorted(
        (r for r in reviews if is_eligible(r)),
        key=lambda r: selection_key(r["reviewId"]),
    )
    result.eligible = len(eligible)

    pools: dict[str, list[dict[str, Any]]] = {"tier1": [], "enriched_other": []}
    leftovers: list[dict[str, Any]] = []
    for review in eligible:
        stratum = _stratum_of(review)
        if stratum is None:
            leftovers.append(review)
        else:
            pools[stratum].append(review)

    taken: set[str] = set()
    carry = 0

    for stratum in ("tier1", "enriched_other"):
        want = targets[stratum] + carry
        pool = [r for r in pools[stratum] if r["reviewId"] not in taken]
        chosen = pool[:want]
        carry = want - len(chosen)
        if carry:
            result.shortfalls[stratum] = carry
        result.selected[stratum] = [r["reviewId"] for r in chosen]
        taken.update(result.selected[stratum])

    # The random slice draws from everything still unselected, including reviews
    # that happen to match a jargon pattern. That is intentional: it keeps the
    # random slice an unbiased sample of substantive reviews.
    want = targets["random"] + carry
    pool = [r for r in eligible if r["reviewId"] not in taken]
    chosen = pool[:want]
    if want - len(chosen):
        result.shortfalls["random"] = want - len(chosen)
    result.selected["random"] = [r["reviewId"] for r in chosen]

    return result


def golden_set_hash(review_ids: Sequence[str]) -> str:
    """Fingerprint of the frozen golden set, recorded in the split manifest."""
    joined = "\n".join(sorted(review_ids))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
