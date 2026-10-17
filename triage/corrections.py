"""Annotator corrections to the golden set.

The golden set that was labeled first is never edited in place. Changes live in
`data/golden/corrections.jsonl`, one line per review, and scoring can run with or
without them. Both numbers get published.

Why keep them separate rather than just fixing the file: the review queue that
surfaces candidates is selected by the system's own output, so corrections made
from it can only move the answer key towards the system. Keeping the original
intact means that bias stays visible and measurable instead of being absorbed
into a single revised number.

Each line records the old label as well as the new one, so a correction can be
checked later and so a stale correction (written against a label that has since
changed) is caught rather than applied silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from triage import paths
from triage.jsonl_io import read_jsonl, write_jsonl
from triage.taxonomy import LabelError, validate_labels

KEEP = "keep"
CHANGE = "change"
ACTIONS = (KEEP, CHANGE)


class CorrectionError(ValueError):
    """A correction file is malformed or does not match the golden set."""


@dataclass(frozen=True)
class Correction:
    review_id: str
    action: str
    old_categories: tuple[str, ...]
    old_severity: str | None
    new_categories: tuple[str, ...]
    new_severity: str | None
    reason: str

    @property
    def changes_anything(self) -> bool:
        return self.action == CHANGE and (
            self.new_categories != self.old_categories
            or self.new_severity != self.old_severity
        )


def _normalise_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CorrectionError(f"expected a list of category ids, got {value!r}")
    return tuple(sorted(str(item) for item in value))


def load_corrections(path: Path | None = None) -> list[Correction]:
    """Read the corrections file. A missing file simply means no corrections."""
    path = path or paths.GOLDEN_CORRECTIONS
    if not path.exists():
        return []

    corrections: list[Correction] = []
    seen: set[str] = set()
    for row in read_jsonl(path):
        review_id = str(row.get("reviewId") or "").strip()
        if not review_id:
            raise CorrectionError(f"a correction line has no reviewId: {row!r}")
        if review_id in seen:
            raise CorrectionError(f"duplicate correction for {review_id}")
        seen.add(review_id)

        action = str(row.get("action") or KEEP).strip().lower()
        if action not in ACTIONS:
            raise CorrectionError(
                f"{review_id}: action must be one of {ACTIONS}, got {action!r}"
            )

        corrections.append(
            Correction(
                review_id=review_id,
                action=action,
                old_categories=_normalise_list(row.get("old_categories")),
                old_severity=row.get("old_severity") or None,
                new_categories=_normalise_list(row.get("new_categories")),
                new_severity=row.get("new_severity") or None,
                reason=str(row.get("reason") or "").strip(),
            )
        )
    return corrections


def validate_against_gold(
    corrections: list[Correction], gold_rows: list[dict[str, Any]]
) -> list[Correction]:
    """Check every correction and return the ones that actually change a label."""
    by_id = {row["reviewId"]: row for row in gold_rows}
    applied: list[Correction] = []

    for correction in corrections:
        if correction.review_id not in by_id:
            raise CorrectionError(
                f"{correction.review_id}: not in the golden set"
            )
        row = by_id[correction.review_id]
        current = tuple(sorted(row.get("categories") or []))

        # A correction written against an older label must not be applied blindly.
        if correction.old_categories and correction.old_categories != current:
            raise CorrectionError(
                f"{correction.review_id}: correction records old label "
                f"{list(correction.old_categories)} but the golden set now says "
                f"{list(current)}; re-check it"
            )

        if correction.action == KEEP:
            continue
        if not correction.changes_anything:
            continue
        if not correction.reason:
            raise CorrectionError(
                f"{correction.review_id}: a change needs a reason, so it can be "
                "checked later"
            )
        try:
            validate_labels(correction.new_categories, correction.new_severity)
        except LabelError as error:
            raise CorrectionError(f"{correction.review_id}: {error}") from error
        applied.append(correction)

    return applied


def apply_to_rows(
    gold_rows: list[dict[str, Any]], corrections: list[Correction]
) -> tuple[list[dict[str, Any]], list[Correction]]:
    """Return corrected golden rows plus the corrections that were applied."""
    applied = validate_against_gold(corrections, gold_rows)
    changes = {c.review_id: c for c in applied}

    corrected: list[dict[str, Any]] = []
    for row in gold_rows:
        correction = changes.get(row["reviewId"])
        if correction is None:
            corrected.append(row)
            continue
        updated = dict(row)
        updated["categories"] = list(correction.new_categories)
        updated["severity"] = correction.new_severity
        updated["corrected"] = True
        updated["correction_reason"] = correction.reason
        corrected.append(updated)
    return corrected, applied


def write_scaffold(
    path: Path,
    candidates: list[dict[str, Any]],
) -> int:
    """Write a pre-filled corrections file for the annotator to edit.

    Every candidate starts as `keep`, so the file is a no-op until edited. To
    change a label, switch `action` to "change", edit `new_categories` and
    `new_severity`, and write a `reason`.
    """
    rows = [
        {
            "reviewId": candidate["reviewId"],
            "action": KEEP,
            "old_categories": list(candidate["gold_categories"]),
            "old_severity": candidate["gold_severity"],
            "new_categories": list(candidate["gold_categories"]),
            "new_severity": candidate["gold_severity"],
            "model_said_categories": list(candidate["model_categories"]),
            "model_said_severity": candidate.get("model_severity"),
            "reason": "",
        }
        for candidate in candidates
    ]
    return write_jsonl(path, rows)
