"""Heuristics used ONLY to stratify golden-set sampling.

Important: this file is **not** a jargon pack and must never be used as one.

Its job is to make the hand-labeled golden set contain enough jargon-bearing and
enough "high star rating but real complaint" reviews for the pack OFF/ON
comparison to be measurable at all. A uniform random sample of this corpus would
be roughly 75% one-word praise.

The authoritative definition of "this review contains game jargon" is the
`has_jargon` flag the annotator sets by hand during labeling. These regexes only
decide which reviews get *offered* for labeling.

Tiers:
  TIER1 - game-specific vocabulary a non-player would not understand.
          Deliberately excludes the game's own name and generic gaming words
          (loot, squad, score, board, team, match, coins) because those inflate
          counts without being jargon.
  TIER2 - domain words that are weaker evidence of jargon but often accompany
          real, game-specific complaints.
"""

from __future__ import annotations

import re

TIER1_PATTERNS: dict[str, str] = {
    "Clash of Clans": (
        r"(?:\bth\s?-?\s?\d{1,2}\b|townhall|town hall|\bcwl\b|clan war|war weight"
        r"|builder base|builder hall|\bbh\d+|\bhog(?:s| rider)|barch|dark elixir"
        r"|gold pass|legend league|hero hall|ore converter|wall wrecker"
        r"|clan capital|\bqc\b|queen charge)"
    ),
    "Candy Crush Saga": (
        r"(?:striped candy|striped|colou?r bomb|piggy bank|lolli|licorice"
        r"|legendary level|wooden block|gold bar|\bjelly\b|booster|sugar drop"
        r"|dreamworld|\bfish\b|chocolate box)"
    ),
    # Held-out games: present so the sampler can be pointed at them later
    # without code changes, but unused in this round's eval.
    "PUBG Mobile": (
        r"(?:erangel|miramar|sanhok|livik|vikendi|karakin|\btdm\b|payload"
        r"|metro royale|\buc\b|royale pass|\brp\b|\btpp\b|\bfpp\b|aim assist"
        r"|m416|\bakm\b|\bawm\b|kar98|bot lobby|conqueror|gyroscope|\bemulator\b"
        r"|aimbot|\bobb\b|\bmythic\b|\bcrate\b|recoil)"
    ),
    "Subway Surfers": (
        r"(?:hoverboard|mystery box|super sneakers|coin magnet|jetpack"
        r"|score ?booster|world tour|season hunt|word hunt|top run|\byutani\b"
        r"|prince k|super mystery|headstart)"
    ),
}

TIER2_PATTERNS: dict[str, str] = {
    "Clash of Clans": (
        r"(?:\bheroes?\b|max(?:ed|ing)\b|matchmaking|\bclan\b|\btroops?\b|\blab\b"
        r"|\bpet\b|\braid\b)"
    ),
    "Candy Crush Saga": (
        r"(?:\blives\b|\bmoves\b|hard level|rigged|chocolate|\bcandies\b"
        r"|\bepisode\b|hammer)"
    ),
    "PUBG Mobile": r"(?:\bhacker|\bcheater|\bping\b|\bfps\b|\bsensitivity\b|\bskin\b)",
    "Subway Surfers": r"(?:\bcharacter\b|\boutfit\b|\bmission\b|\bupgrade\b)",
}

# Signals a complaint even when the star rating is high. Used to pull the
# "4-5 stars but actually reporting a problem" reviews into the golden set.
COMPLAINT_CUE = (
    r"(?:\bbut\b|however|fix|bug|lag|crash|expensive|too hard|annoying|\bads?\b"
    r"|glitch|rigged|freeze|hack|\bworse\b|\bstuck\b|can'?t|cannot|won'?t)"
)

# Very common English function words. Used as a cheap language filter because the
# dataset has no language column. Non-Latin script is only ~1-2% of the corpus,
# so a stopword test is enough and avoids a heavy dependency.
ENGLISH_CUE = (
    r"\b(?:the|and|is|it|this|game|i|you|to|of|but|my|very|not|for|so|please|why"
    r"|when|they|are|have)\b"
)

_TIER1 = {game: re.compile(pattern) for game, pattern in TIER1_PATTERNS.items()}
_TIER2 = {game: re.compile(pattern) for game, pattern in TIER2_PATTERNS.items()}
_COMPLAINT = re.compile(COMPLAINT_CUE)
_ENGLISH = re.compile(ENGLISH_CUE)


def has_tier1_jargon(game: str, text: str) -> bool:
    pattern = _TIER1.get(game)
    return bool(pattern and pattern.search(text.lower()))


def has_tier2_jargon(game: str, text: str) -> bool:
    pattern = _TIER2.get(game)
    return bool(pattern and pattern.search(text.lower()))


def has_complaint_cue(text: str) -> bool:
    return bool(_COMPLAINT.search(text.lower()))


def looks_english(text: str) -> bool:
    return bool(_ENGLISH.search(text.lower()))


def word_count(text: str) -> int:
    return len(text.split())
