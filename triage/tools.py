"""The actual work behind the MCP tools, as plain functions.

Kept separate from the MCP server so the behaviour can be tested directly,
without a protocol round-trip and without the SDK installed. mcp_server/server.py
is a thin wrapper that registers these with the official SDK.

The one design point that matters for the experiment:

    get_jargon_pack is the ONLY difference between the pack OFF and pack ON
    conditions.

Pack OFF is not a different prompt, a different skill or a different model. It is
this same function returning a shape-identical payload with zero terms, chosen by
the TRIAGE_PACK_MODE environment variable. Every response states which mode it
was in, so a run trace proves which condition it belonged to.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from triage import packs, paths
from triage.jsonl_io import read_json, read_jsonl, write_json
from triage.taxonomy import load_taxonomy

PACK_MODE_ENV = "TRIAGE_PACK_MODE"
RUNS_DIR_ENV = "TRIAGE_RUNS_DIR"

PACK_ON = "on"
PACK_OFF = "off"

#: Fields that exist only in the hand-made answer key. get_reviews must never
#: return any of them; tests/test_tools.py enforces that.
GOLDEN_LABEL_FIELDS = ("categories", "severity", "has_jargon", "unclear", "note", "labeled_at")

#: Fields that reveal why a review was sampled. Withheld for the same reason.
SAMPLING_HINT_FIELDS = (
    "stratum",
    "slice",
    "split",
    "tier1_jargon",
    "tier2_jargon",
    "complaint_cue",
    "looks_english",
)

#: What a triaged review is expected to carry back.
REVIEW_PUBLIC_FIELDS = ("reviewId", "game", "content", "score", "date", "appVersion")


def pack_mode() -> str:
    """'on' or 'off'. Anything unrecognised counts as 'on'."""
    value = (os.environ.get(PACK_MODE_ENV) or PACK_ON).strip().lower()
    return PACK_OFF if value in (PACK_OFF, "0", "false", "no") else PACK_ON


def runs_dir() -> Path:
    return Path(os.environ.get(RUNS_DIR_ENV) or paths.RUNS_DIR)


def list_games() -> dict[str, Any]:
    games = packs.list_games()
    return {"games": games, "count": len(games), "source": "directory scan of packs/*.yaml"}


def get_taxonomy() -> dict[str, Any]:
    taxonomy = load_taxonomy()
    return {
        "version": taxonomy.version,
        "description": taxonomy.description,
        "labeling_rules": taxonomy.labeling_rules,
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "definition": category.definition,
                "includes": list(category.includes),
                "excludes": list(category.excludes),
                "exclusive": category.exclusive,
                "severity_guidance": category.severity_guidance,
            }
            for category in taxonomy.categories
        ],
        "severity": taxonomy.severity,
        "boundaries": taxonomy.boundaries,
    }


def get_jargon_pack(game: str) -> dict[str, Any]:
    """The game's vocabulary pack, or a shape-identical empty one."""
    game = (game or "").strip()
    if not game:
        raise ValueError("'game' is required")

    mode = pack_mode()
    if mode == PACK_OFF:
        payload = packs.empty_pack_payload(
            game, reason=f"jargon pack disabled for this run ({PACK_MODE_ENV}=off)"
        )
    else:
        try:
            payload = packs.load_pack(game).as_dict()
        except packs.PackError as error:
            payload = packs.empty_pack_payload(game, reason=str(error))

    # Always reported, in both conditions, so a trace can be checked rather than
    # trusted. The eval runner aborts a run whose traces disagree with the
    # condition it asked for.
    payload["pack_mode"] = mode
    return payload


def get_reviews(
    game: str = "",
    split: str = "golden",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """A page of reviews to triage, carrying no labels and no sampling hints."""
    game = (game or "").strip()
    split = (split or "golden").strip().lower()
    limit = int(limit)
    offset = int(offset)

    if split not in ("golden", "dev"):
        raise ValueError("'split' must be 'golden' or 'dev'")
    if not 1 <= limit <= 200:
        raise ValueError("'limit' must be between 1 and 200")
    if offset < 0:
        raise ValueError("'offset' must not be negative")

    rows = _load_reviews(split)
    if game:
        rows = [row for row in rows if row["game"].lower() == game.lower()]

    withheld = excluded_review_ids()
    before = len(rows)
    rows = [row for row in rows if row["reviewId"] not in withheld]

    window = rows[offset : offset + limit]
    return {
        "split": split,
        "game": game or "all",
        "total_matching": len(rows),
        "withheld": before - len(rows),
        "offset": offset,
        "returned": len(window),
        "reviews": [
            {field: row.get(field) for field in REVIEW_PUBLIC_FIELDS} for row in window
        ],
    }


def excluded_review_ids() -> set[str]:
    """Reviews withheld from eval runs.

    Reads a file of ids and reasons only, never the answer key: reviews the
    annotator could not label would otherwise be scored as if the model had
    failed at something a human managed.
    """
    path = paths.EXCLUDED_REVIEWS
    if not path.exists():
        return set()
    payload = read_json(path)
    return {str(item["reviewId"]) for item in payload.get("excluded", [])}


def _load_reviews(split: str) -> list[dict[str, Any]]:
    """Read reviews for a split.

    Deliberately reads the unlabeled pool, never data/golden/golden_set.jsonl:
    that file holds the hand-made answer key, and handing it to the system being
    evaluated would invalidate every result.
    """
    pool_path = paths.GOLDEN_DIR / "golden_pool.jsonl"
    if split == "golden" and pool_path.exists():
        return read_jsonl(pool_path)
    if not paths.REVIEWS_JSONL.exists():
        raise ValueError(
            f"no review data available for split '{split}'; run scripts/prepare_data.py"
        )
    return [row for row in read_jsonl(paths.REVIEWS_JSONL) if row.get("split") == split]


def save_triage(
    run_id: str,
    results: list[dict[str, Any]],
    game: str = "",
    issue_groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist one run's triage output so scoring can happen offline later."""
    run_id = (run_id or "").strip()
    if not run_id or any(char in run_id for char in '/\\:*?"<>|'):
        raise ValueError("'run_id' is required and must be a safe directory name")
    if not isinstance(results, list) or not results:
        raise ValueError("'results' must be a non-empty list of per-review triage objects")

    payload = {
        "run_id": run_id,
        "game": game or None,
        "pack_mode": pack_mode(),
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "result_count": len(results),
        "results": results,
        "issue_groups": issue_groups or [],
    }
    out_path = runs_dir() / run_id / "output.json"
    write_json(out_path, payload)
    return {"saved": str(out_path), "result_count": len(results), "pack_mode": payload["pack_mode"]}
