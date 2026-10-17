"""Blind re-labeling of a sample of the golden set.

The label review queue lists reviews where the system disagreed with the
annotator. Correcting straight from that list would be biased: the list is
selected by the system's own output, so every correction can only move the answer
key towards the system, and there is no way to tell a genuine fix from ordinary
annotator noise.

This module builds a blind task instead. It mixes

* the **queue** reviews, where all runs agreed on a label that differs from the
  annotator's, and
* a **control** sample of reviews where all runs agreed *with* the annotator,

shuffles them with a fixed seed, and hides which is which. The annotator labels
every one from scratch, seeing neither their old label nor the system's.

The controls are what make the result readable. If the annotator reproduces their
own control labels but changes many queue labels, the queue found real errors. If
they also change a similar share of controls, re-labeling is mostly noise and the
corrections should not be trusted. Either way the number is measured rather than
assumed.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from triage import paths
from triage.jsonl_io import append_jsonl, iter_jsonl, read_json, write_json

#: Fixed so the task list is identical on any machine and any rerun.
RELABEL_SEED = 20261017
DEFAULT_CONTROL_COUNT = 30

SOURCE_QUEUE = "queue"
SOURCE_CONTROL = "control"

#: Offered as fixed choices so reasons are comparable afterwards, rather than
#: free text that cannot be counted.
CHANGE_REASONS = {
    "misapplied_rule": "I applied the rule wrongly",
    "missed_second_issue": "I missed a second issue",
    "severity_misjudged": "I judged the severity wrongly",
    "bug_as_feature_request": "I read a bug as a feature request",
    "other": "Other",
}

RELABEL_MANIFEST = paths.GOLDEN_DIR / "relabel_manifest.json"
RELABEL_PARTIAL = paths.GOLDEN_DIR / "relabel.partial.jsonl"


@dataclass(frozen=True)
class Task:
    review_id: str
    source: str
    order: int


def unanimous_predictions(runs_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """reviewId -> the label every completed run agreed on, plus its rationales.

    Reviews where the runs disagreed with each other are left out: they are not a
    clean signal in either direction.
    """
    runs_dir = runs_dir or paths.RUNS_DIR
    collected: dict[str, list[dict[str, Any]]] = {}
    for meta_path in sorted(runs_dir.glob("*/meta.json")):
        meta = read_json(meta_path)
        if meta.get("status") != "ok":
            continue
        output_path = meta_path.parent / "output.json"
        if not output_path.exists():
            continue
        for result in read_json(output_path).get("results", []):
            review_id = result.get("reviewId")
            if not review_id:
                continue
            collected.setdefault(review_id, []).append(
                {
                    "categories": tuple(sorted(result.get("categories") or [])),
                    "severity": result.get("severity"),
                    "rationale": (result.get("rationale") or "").strip(),
                }
            )

    unanimous: dict[str, dict[str, Any]] = {}
    for review_id, entries in collected.items():
        category_sets = {entry["categories"] for entry in entries}
        if len(category_sets) != 1:
            continue
        severities = {entry["severity"] for entry in entries}
        rationales: list[str] = []
        for entry in entries:
            if entry["rationale"] and entry["rationale"] not in rationales:
                rationales.append(entry["rationale"])
        unanimous[review_id] = {
            "categories": list(next(iter(category_sets))),
            # Whether the runs also agreed on severity. Without this flag a review
            # where they disagreed among themselves would look like a
            # disagreement with the annotator, which it is not.
            "severity_unanimous": len(severities) == 1,
            "severity": next(iter(severities)) if len(severities) == 1 else None,
            "severities": sorted(s for s in severities if s),
            "rationales": rationales[:3],
            "runs": len(entries),
        }
    return unanimous


def build_task_list(
    gold: dict[str, Any],
    unanimous: dict[str, dict[str, Any]],
    control_count: int = DEFAULT_CONTROL_COUNT,
    expected_runs: int = 6,
    seed: int = RELABEL_SEED,
) -> list[Task]:
    """Queue reviews plus a seeded control sample, shuffled, provenance hidden."""
    queue_ids: list[str] = []
    agree_ids: list[str] = []

    for review_id, agreed in sorted(unanimous.items()):
        if review_id not in gold or agreed["runs"] < expected_runs:
            continue
        gold_categories = sorted(gold[review_id].categories)
        model_categories = sorted(agreed["categories"])
        if model_categories != gold_categories:
            queue_ids.append(review_id)
        elif agreed["severity_unanimous"] and agreed["severity"] != gold[review_id].severity:
            # Categories match but every run agreed on a different severity.
            queue_ids.append(review_id)
        elif agreed["severity_unanimous"]:
            agree_ids.append(review_id)
        # Runs that disagreed with each other on severity are neither a clean
        # disagreement nor a clean agreement, so they are left out entirely.

    rng = random.Random(seed)
    controls = sorted(agree_ids)
    rng.shuffle(controls)
    controls = controls[:control_count]

    tasks = [Task(rid, SOURCE_QUEUE, 0) for rid in queue_ids]
    tasks += [Task(rid, SOURCE_CONTROL, 0) for rid in controls]

    order_rng = random.Random(seed + 1)
    order_rng.shuffle(tasks)
    return [Task(t.review_id, t.source, i) for i, t in enumerate(tasks)]


def write_manifest(tasks: list[Task], path: Path | None = None) -> dict[str, Any]:
    """Record the task list and which group each review came from.

    Committed so the result can be analysed later, and deliberately *not* sent to
    the labeling page: seeing that a review was queued would tell the annotator
    the system disagreed with them, which is the whole thing being controlled for.
    """
    path = path or RELABEL_MANIFEST
    payload = {
        "description": (
            "Blind re-labeling task list. The `source` field is for analysis only "
            "and is never shown during labeling."
        ),
        "seed": RELABEL_SEED,
        "counts": {
            SOURCE_QUEUE: sum(1 for t in tasks if t.source == SOURCE_QUEUE),
            SOURCE_CONTROL: sum(1 for t in tasks if t.source == SOURCE_CONTROL),
            "total": len(tasks),
        },
        "fingerprint": hashlib.sha256(
            "\n".join(f"{t.order}:{t.review_id}:{t.source}" for t in tasks).encode("utf-8")
        ).hexdigest()[:16],
        "tasks": [
            {"order": t.order, "reviewId": t.review_id, "source": t.source} for t in tasks
        ],
    }
    write_json(path, payload)
    return payload


def load_manifest(path: Path | None = None) -> dict[str, Any] | None:
    path = path or RELABEL_MANIFEST
    if not path.exists():
        return None
    return read_json(path)


class RelabelStore:
    """Append-only log of blind labels, replayed last-write-wins."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or RELABEL_PARTIAL

    def load(self) -> dict[str, dict[str, Any]]:
        state: dict[str, dict[str, Any]] = {}
        if not self.path.exists():
            return state
        for record in iter_jsonl(self.path):
            review_id = record.get("reviewId")
            if review_id:
                state[str(review_id)] = record
        return state

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        append_jsonl(self.path, record)
        return record
