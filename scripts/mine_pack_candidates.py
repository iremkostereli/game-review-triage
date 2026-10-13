"""Mine jargon-term candidates from the dev split.

    uv run scripts/mine_pack_candidates.py --game "Clash of Clans"

Reads the DEV split only, and asserts it. Golden reviews are held out, so a term
discovered from one would contaminate the very comparison this project measures.

How a candidate is found, rather than recalled: an n-gram is a candidate when it
appears repeatedly in one game's reviews and is rare or absent in the other
game's. That contrast is what separates game vocabulary ("town hall", "color
bomb") from ordinary review language ("good game", "too many ads"), without
anyone writing a word list from memory first.

The output is a shortlist for a human to verify. It proposes no meanings: those
are written by hand, from official publisher sources where they exist.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import paths
from triage.jsonl_io import read_jsonl, write_json

#: Ordinary words that carry no game-specific meaning. Kept deliberately short:
#: the cross-game contrast does most of the filtering.
STOPWORDS = {
    "a", "about", "after", "again", "all", "also", "always", "am", "an", "and", "any",
    "are", "as", "at", "back", "bad", "be", "because", "been", "best", "better", "but",
    "by", "can", "cant", "do", "dont", "even", "every", "first", "for", "from", "fun",
    "game", "games", "get", "give", "go", "good", "got", "great", "has", "have", "i",
    "if", "im", "in", "is", "it", "its", "just", "like", "love", "make", "many", "me",
    "more", "most", "much", "my", "need", "new", "no", "not", "now", "of", "on", "one",
    "only", "or", "other", "out", "play", "played", "player", "players", "playing",
    "please", "pls", "plz", "really", "right", "say", "see", "should", "so", "some",
    "still", "such", "that", "the", "their", "them", "then", "there", "they", "thing",
    "think", "this", "time", "to", "too", "update", "use", "very", "want", "was", "way",
    "we", "well", "what", "when", "which", "who", "why", "will", "with", "without",
    "worst", "would", "you", "your", "it's", "don't", "can't",
}

#: Shapes that are almost always game vocabulary regardless of frequency.
PATTERNS = [
    re.compile(r"\bth\s?-?\s?\d{1,2}\b", re.I),      # town hall level
    re.compile(r"\bbh\s?-?\s?\d{1,2}\b", re.I),      # builder hall level
    re.compile(r"\b[a-z]{2,4}\d{1,3}\b", re.I),      # m416, kar98, th13
    re.compile(r"\b\d{1,3}k\+?\b", re.I),            # 19k levels
]

TOKEN = re.compile(r"[a-z][a-z'\-]*\d*|\d+k?\+?", re.I)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN.finditer(text)]


def ngrams(tokens: list[str], size: int) -> list[str]:
    return [" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)]


def is_interesting(phrase: str) -> bool:
    """Drop phrases made entirely of ordinary review language."""
    words = phrase.split()
    if all(word in STOPWORDS for word in words):
        return False
    # A multi-word phrase must carry at least one non-stopword of real length.
    return any(word not in STOPWORDS and len(word) > 2 for word in words)


def load_dev(game: str) -> list[dict[str, Any]]:
    rows = read_jsonl(paths.REVIEWS_JSONL)
    dev = [row for row in rows if row["split"] == "dev"]
    assert all(row["split"] != "golden" for row in dev), "golden review leaked into mining"
    return [row for row in dev if row["game"].lower() == game.lower()]


def count_phrases(reviews: list[dict[str, Any]], max_size: int = 3) -> Counter:
    counts: Counter = Counter()
    for review in reviews:
        tokens = tokenize(review["content"])
        seen: set[str] = set()
        for size in range(1, max_size + 1):
            for phrase in ngrams(tokens, size):
                if phrase in seen or not is_interesting(phrase):
                    continue
                seen.add(phrase)
                counts[phrase] += 1  # document frequency, not raw count
    return counts


def mine(game: str, other_game: str, min_count: int, top: int) -> dict[str, Any]:
    mine_reviews = load_dev(game)
    other_reviews = load_dev(other_game)

    here = count_phrases(mine_reviews)
    there = count_phrases(other_reviews)
    here_total = len(mine_reviews)
    there_total = len(other_reviews)

    candidates = []
    for phrase, count in here.items():
        if count < min_count:
            continue
        rate_here = count / here_total
        rate_there = there.get(phrase, 0) / there_total
        # Distinctiveness: how much more this game's players say it. The +0.001
        # keeps a phrase absent from the other game from dividing by zero.
        distinctiveness = rate_here / (rate_there + 0.001)
        pattern_hit = any(pattern.search(phrase) for pattern in PATTERNS)
        if distinctiveness < 3 and not pattern_hit:
            continue

        examples = [
            {"reviewId": review["reviewId"], "quote": _snippet(review["content"], phrase)}
            for review in mine_reviews
            if phrase in review["content"].lower()
        ][:3]

        candidates.append(
            {
                "phrase": phrase,
                "reviews_mentioning": count,
                "other_game_mentions": there.get(phrase, 0),
                "distinctiveness": round(distinctiveness, 1),
                "pattern_match": pattern_hit,
                "examples": examples,
            }
        )

    candidates.sort(key=lambda item: (-item["distinctiveness"], -item["reviews_mentioning"]))
    return {
        "game": game,
        "contrast_game": other_game,
        "dev_reviews_scanned": here_total,
        "split": "dev",
        "min_count": min_count,
        "candidate_count": len(candidates[:top]),
        "candidates": candidates[:top],
    }


def _snippet(content: str, phrase: str, width: int = 90) -> str:
    lowered = content.lower()
    index = lowered.find(phrase)
    if index < 0:
        return content[:width]
    start = max(0, index - width // 3)
    return content[start : start + width].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", default="Clash of Clans")
    parser.add_argument("--contrast", default=None, help="game to contrast against")
    parser.add_argument("--min-count", type=int, default=3)
    parser.add_argument("--top", type=int, default=60)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    contrast = args.contrast or next(
        game for game in paths.EVAL_GAMES if game.lower() != args.game.lower()
    )
    result = mine(args.game, contrast, args.min_count, args.top)

    print(f"{result['game']}: {result['candidate_count']} candidates "
          f"from {result['dev_reviews_scanned']} dev reviews "
          f"(contrast: {result['contrast_game']})\n")
    for item in result["candidates"]:
        flag = " [shape]" if item["pattern_match"] else ""
        print(f"  {item['phrase']:<28} reviews={item['reviews_mentioning']:>3} "
              f"other={item['other_game_mentions']:>3} "
              f"distinct={item['distinctiveness']:>6}{flag}")

    if args.out:
        write_json(args.out, result)
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
