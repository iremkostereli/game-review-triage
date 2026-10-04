"""Storage for hand-made labels.

Design: the labeling tool never rewrites a file in place. Every save appends one
record to an append-only log, and the current state is the replay of that log
with the last write per review winning. Changing your mind about review 12 after
labeling 80 more is therefore just another append, and an interrupted write can
at worst lose the single record being written.

The log lives at data/golden/labels.partial.jsonl and is gitignored. The finished
answer key is exported to data/golden/golden_set.jsonl, which IS committed,
because it is the most valuable artifact in the repo and the offline scoring path
has to work without the raw dataset.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from triage import paths
from triage.jsonl_io import append_jsonl, iter_jsonl, write_jsonl
from triage.taxonomy import LabelError, Taxonomy, validate_label_record

#: Fields of a label record, in the order they are written.
LABEL_FIELDS = ("reviewId", "categories", "severity", "has_jargon", "unclear", "note")

#: Pool fields carried into the exported golden set so scoring needs no raw data.
POOL_FIELDS = ("game", "content", "score", "date", "appVersion", "words")


def normalize(record: dict[str, Any]) -> dict[str, Any]:
    """Coerce a label payload into the canonical shape."""
    severity = record.get("severity") or None
    return {
        "reviewId": str(record["reviewId"]),
        "categories": sorted(str(c) for c in record.get("categories", [])),
        "severity": severity,
        "has_jargon": bool(record.get("has_jargon", False)),
        "unclear": bool(record.get("unclear", False)),
        "note": str(record.get("note", "") or "").strip(),
    }


class LabelStore:
    """Append-only label log with last-write-wins replay."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or paths.LABELS_PARTIAL

    def load(self) -> dict[str, dict[str, Any]]:
        """Replay the log into {reviewId: record}. Later writes overwrite earlier."""
        state: dict[str, dict[str, Any]] = {}
        if not self.path.exists():
            return state
        for record in iter_jsonl(self.path):
            review_id = record.get("reviewId")
            if review_id:
                state[str(review_id)] = record
        return state

    def save(self, record: dict[str, Any], taxonomy: Taxonomy | None = None) -> dict[str, Any]:
        """Validate and append one label. Returns the stored record."""
        stored = normalize(record)
        validate_label_record(stored, taxonomy)
        stored["labeled_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        append_jsonl(self.path, stored)
        return stored

    def counts(self, pool_ids: Iterable[str]) -> dict[str, int]:
        """Progress summary against the pool being labeled."""
        state = self.load()
        pool = list(pool_ids)
        labeled = [rid for rid in pool if rid in state]
        return {
            "total": len(pool),
            "labeled": len(labeled),
            "remaining": len(pool) - len(labeled),
            "noted": sum(1 for rid in labeled if state[rid].get("note")),
            "unclear": sum(1 for rid in labeled if state[rid].get("unclear")),
        }


def export_golden_set(
    pool: list[dict[str, Any]],
    store: LabelStore | None = None,
    out_path: Path | None = None,
    taxonomy: Taxonomy | None = None,
    require_complete: bool = True,
) -> dict[str, Any]:
    """Write the finished golden set, validating every row first.

    Raises LabelError listing what is wrong rather than writing a partial file,
    so an incomplete or invalid answer key can never silently become the thing
    the eval is scored against.
    """
    store = store or LabelStore()
    out_path = out_path or paths.GOLDEN_SET
    state = store.load()

    by_id = {record["reviewId"]: record for record in pool}
    missing = [rid for rid in by_id if rid not in state]
    if missing and require_complete:
        raise LabelError(
            f"{len(missing)} of {len(by_id)} reviews are not labeled yet; "
            f"first few: {sorted(missing)[:5]}"
        )

    problems: list[str] = []
    rows: list[dict[str, Any]] = []
    for review_id, review in sorted(by_id.items()):
        record = state.get(review_id)
        if record is None:
            continue
        try:
            validate_label_record(record, taxonomy)
        except LabelError as error:
            problems.append(f"{review_id}: {error}")
            continue
        row = {field: review.get(field) for field in POOL_FIELDS}
        row["reviewId"] = review_id
        for field in LABEL_FIELDS:
            if field != "reviewId":
                row[field] = record.get(field)
        row["labeled_at"] = record.get("labeled_at")
        rows.append(row)

    if problems:
        raise LabelError("invalid label records:\n  " + "\n  ".join(problems))

    write_jsonl(out_path, rows)
    return {
        "written": len(rows),
        "path": str(out_path),
        "unlabeled": len(missing),
        "noted": sum(1 for row in rows if row.get("note")),
        "unclear": sum(1 for row in rows if row.get("unclear")),
    }
