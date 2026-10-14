"""Prepare the review corpus: filter, enrich, and freeze a dev/golden split.

Run this once before anything else:

    python scripts/prepare_data.py

Outputs
-------
data/interim/reviews.jsonl      all eval-game reviews with derived fields (gitignored)
data/golden/golden_pool.jsonl   the 180 reviews to hand-label (committed)
data/splits/split_manifest.json the frozen split: ids, counts, fingerprint

The golden pool is committed because the raw dataset is not. That keeps the
offline path (recompute metrics, run the tests) working for anyone who clones the
repo without downloading 10k reviews from Kaggle.

This is the only step that needs pandas.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import paths, sampling, sampling_terms
from triage.jsonl_io import write_json, write_jsonl

REQUIRED_COLUMNS = ["app", "reviewId", "content", "score", "thumbsUpCount", "date", "appVersion"]


def load_reviews(csv_path: Path) -> list[dict[str, Any]]:
    """Read the raw CSV and derive the fields sampling and labeling need."""
    import pandas as pd

    frame = pd.read_csv(csv_path, encoding="utf-8")

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise SystemExit(f"Raw CSV is missing expected columns: {missing}")

    frame = frame[frame["app"].isin(paths.EVAL_GAMES)].copy()
    frame["content"] = frame["content"].astype(str).str.strip()
    frame = frame[frame["content"].str.len() > 0]

    reviews: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        text = str(row.content)
        game = str(row.app)
        reviews.append(
            {
                "reviewId": str(row.reviewId),
                "game": game,
                "content": text,
                "score": int(row.score),
                "thumbsUpCount": int(row.thumbsUpCount),
                "date": str(row.date),
                "appVersion": None if _is_blank(row.appVersion) else str(row.appVersion),
                "words": sampling_terms.word_count(text),
                "chars": len(text),
                # Derived sampling signals. These stratify labeling only; the
                # authoritative jargon judgement is the annotator's has_jargon flag.
                "looks_english": sampling_terms.looks_english(text),
                "tier1_jargon": sampling_terms.has_tier1_jargon(game, text),
                "tier2_jargon": sampling_terms.has_tier2_jargon(game, text),
                "complaint_cue": sampling_terms.has_complaint_cue(text),
            }
        )

    # Sorting by the deterministic selection key makes every downstream output
    # stable regardless of the order pandas happened to hand us the rows.
    reviews.sort(key=lambda r: sampling.selection_key(r["reviewId"]))
    return reviews


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip().lower() in {"", "nan", "none"}


def drop_duplicate_content(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one review per (game, normalized content).

    The corpus has ~2,650 duplicate strings, nearly all of them one-word praise.
    Duplicates would let the same text land in both the dev and golden splits,
    which would be a subtle leak, and would waste annotator time.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for review in reviews:
        key = (review["game"], " ".join(review["content"].lower().split()))
        if key in seen:
            continue
        seen.add(key)
        unique.append(review)
    return unique


def build_split(reviews: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Assign every review to the golden or dev split and build the manifest."""
    per_game: dict[str, list[dict[str, Any]]] = {game: [] for game in paths.EVAL_GAMES}
    for review in reviews:
        per_game[review["game"]].append(review)

    stratum_of: dict[str, str] = {}
    manifest_games: dict[str, Any] = {}

    for game in paths.EVAL_GAMES:
        drawn = sampling.sample_game(game, per_game[game])
        for stratum, ids in drawn.selected.items():
            for review_id in ids:
                stratum_of[review_id] = stratum
        manifest_games[game] = {
            "reviews_total": len(per_game[game]),
            "golden_eligible": drawn.eligible,
            "golden_total": drawn.total,
            "targets": sampling.TARGETS[game],
            "selected_counts": {s: len(ids) for s, ids in drawn.selected.items()},
            "shortfalls": drawn.shortfalls,
            "golden_ids": {s: sorted(ids) for s, ids in drawn.selected.items()},
        }

    for review in reviews:
        stratum = stratum_of.get(review["reviewId"])
        review["split"] = "golden" if stratum else "dev"
        review["stratum"] = stratum
        review["slice"] = sampling.STRATUM_SLICE[stratum] if stratum else None

    golden_ids = sorted(stratum_of)
    manifest = {
        "description": (
            "Frozen dev/golden split. The golden set is held out: jargon packs are "
            "built from the dev split and official publisher sources only."
        ),
        "min_words": sampling.MIN_WORDS,
        "eval_games": list(paths.EVAL_GAMES),
        "held_out_games": list(paths.HELD_OUT_GAMES),
        "selection": "deterministic: reviews ranked by sha256(reviewId), no RNG",
        "golden_total": len(golden_ids),
        "golden_set_sha256": sampling.golden_set_hash(golden_ids),
        "games": manifest_games,
    }
    return reviews, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=paths.RAW_CSV, help="raw CSV path")
    args = parser.parse_args()

    if not args.raw.exists():
        raise SystemExit(
            f"Raw dataset not found at {args.raw}\n"
            "Download it from https://www.kaggle.com/datasets/araraltawil/game-reviews "
            "and place game_reviews.csv in data/raw/ (see README)."
        )

    reviews = load_reviews(args.raw)
    before = len(reviews)
    reviews = drop_duplicate_content(reviews)
    reviews, manifest = build_split(reviews)

    write_jsonl(paths.REVIEWS_JSONL, reviews)

    # The labeling pool carries no labels and no sampling hints that could bias
    # the annotator: stratum and slice are deliberately withheld from the UI.
    pool = [
        {
            "reviewId": r["reviewId"],
            "game": r["game"],
            "content": r["content"],
            "score": r["score"],
            "date": r["date"],
            "appVersion": r["appVersion"],
            "words": r["words"],
        }
        for r in reviews
        if r["split"] == "golden"
    ]
    pool.sort(key=lambda r: sampling.selection_key(r["reviewId"]))
    write_jsonl(paths.GOLDEN_DIR / "golden_pool.jsonl", pool)

    # Slice membership, committed separately from the pool. Scoring needs it to
    # report the random and enriched slices apart; the labeling UI must not see
    # it, because knowing a review was picked for its jargon would bias the
    # annotator's has_jargon flag, and that flag defines the headline slice.
    write_json(
        paths.GOLDEN_SLICES,
        {
            "description": (
                "Sampling slice per golden review. Not shown during labeling; used "
                "only to break scoring down by slice."
            ),
            "slices": {
                r["reviewId"]: r["slice"] for r in reviews if r["split"] == "golden"
            },
        },
    )
    write_json(paths.SPLIT_MANIFEST, manifest)

    print(f"Loaded {before} reviews for {', '.join(paths.EVAL_GAMES)}")
    print(f"After de-duplicating content: {len(reviews)}")
    print(f"Golden set: {manifest['golden_total']} reviews "
          f"(fingerprint {manifest['golden_set_sha256'][:12]}...)")
    for game in paths.EVAL_GAMES:
        info = manifest["games"][game]
        counts = info["selected_counts"]
        print(
            f"  {game}: golden {info['golden_total']} "
            f"(tier1 {counts['tier1']}, enriched_other {counts['enriched_other']}, "
            f"random {counts['random']}) from {info['golden_eligible']} eligible"
        )
        if info["shortfalls"]:
            print(f"    shortfalls rolled forward: {info['shortfalls']}")
    dev_count = sum(1 for r in reviews if r["split"] == "dev")
    print(f"Dev split (available for jargon-pack mining): {dev_count}")
    print(f"\nWrote {paths.REVIEWS_JSONL}")
    print(f"Wrote {paths.GOLDEN_DIR / 'golden_pool.jsonl'}")
    print(f"Wrote {paths.GOLDEN_SLICES}")
    print(f"Wrote {paths.SPLIT_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
