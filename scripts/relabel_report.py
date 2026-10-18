"""Report on the blind re-labeling pass, and write the corrected answer key.

    uv run scripts/relabel_report.py

No model is called. Reads the blind labels, the original answer key, the task
manifest and the decisions, and reports:

* how often the blind labels reproduced the original ones,
* how that splits between the queued reviews and the controls,
* why labels were changed,

then writes the corrected answer key to its own file. The original
`golden_set.jsonl` is never modified.

The control split is the point of the exercise. A high change rate on queued
reviews together with a low one on controls means the queue found real errors. A
similar rate on both means re-labeling is mostly noise, and the corrections
should not be trusted.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import corrections as corrections_module
from triage import paths, relabel
from triage.jsonl_io import read_jsonl, write_jsonl


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=paths.GOLDEN_DIR / "golden_set_corrected.jsonl")
    args = parser.parse_args()

    manifest = relabel.load_manifest()
    if manifest is None:
        raise SystemExit("no relabel manifest; run scripts/relabel.py first")
    source_of = {t["reviewId"]: t["source"] for t in manifest["tasks"]}

    gold_rows = read_jsonl(paths.GOLDEN_SET)
    original = {row["reviewId"]: row for row in gold_rows}
    blind = relabel.RelabelStore().load()
    decisions = {
        row["reviewId"]: row
        for row in (
            read_jsonl(paths.GOLDEN_CORRECTIONS)
            if paths.GOLDEN_CORRECTIONS.exists()
            else []
        )
    }

    print(f"Task list: {manifest['counts']} (fingerprint {manifest['fingerprint']})")
    print(f"Blind labels recorded: {len(blind)}")
    print(f"Decisions recorded: {len(decisions)}")
    print()

    # ---- blind vs original agreement -------------------------------------
    print("=" * 72)
    print("BLIND LABELS vs ORIGINAL LABELS (before any decision)")
    print("=" * 72)

    counters: dict[str, Counter] = {
        "all": Counter(), relabel.SOURCE_QUEUE: Counter(), relabel.SOURCE_CONTROL: Counter()
    }
    for review_id, record in blind.items():
        row = original.get(review_id)
        if row is None:
            continue
        same_categories = sorted(record.get("categories") or []) == sorted(
            row.get("categories") or []
        )
        same_severity = (record.get("severity") or None) == (row.get("severity") or None)
        same_jargon = bool(record.get("has_jargon")) == bool(row.get("has_jargon"))
        for key in ("all", source_of.get(review_id, "unknown")):
            if key not in counters:
                continue
            counters[key]["n"] += 1
            counters[key]["categories_same"] += same_categories
            counters[key]["severity_same"] += same_severity
            counters[key]["jargon_same"] += same_jargon
            counters[key]["both_same"] += same_categories and same_severity

    header = f"{'group':<10}{'n':>5}{'categories':>14}{'severity':>12}{'both':>10}{'jargon flag':>14}"
    print(header)
    for key, label in (("all", "all"), (relabel.SOURCE_QUEUE, "queue"),
                       (relabel.SOURCE_CONTROL, "control")):
        c = counters[key]
        if not c["n"]:
            continue
        print(f"{label:<10}{c['n']:>5}"
              f"{c['categories_same']:>7} {pct(c['categories_same'], c['n']):>6}"
              f"{c['severity_same']:>6} {pct(c['severity_same'], c['n']):>5}"
              f"{c['both_same']:>5} {pct(c['both_same'], c['n']):>4}"
              f"{c['jargon_same']:>8} {pct(c['jargon_same'], c['n']):>5}")
    print()

    # ---- decisions, split by group ---------------------------------------
    print("=" * 72)
    print("DECISIONS, SPLIT BY GROUP")
    print("=" * 72)
    by_group: dict[str, Counter] = {
        relabel.SOURCE_QUEUE: Counter(), relabel.SOURCE_CONTROL: Counter()
    }
    for review_id in source_of:
        group = source_of[review_id]
        by_group[group]["in_task_list"] += 1
        decision = decisions.get(review_id)
        if decision is None:
            by_group[group]["blind_matched_original"] += 1
        elif decision.get("action") == "change":
            by_group[group]["changed"] += 1
        else:
            by_group[group]["kept_after_review"] += 1

    print(f"{'group':<10}{'reviews':>9}{'blind = original':>18}{'differed':>10}"
          f"{'kept':>7}{'CHANGED':>10}")
    for group, label in ((relabel.SOURCE_QUEUE, "queue"), (relabel.SOURCE_CONTROL, "control")):
        c = by_group[group]
        differed = c["changed"] + c["kept_after_review"]
        print(f"{label:<10}{c['in_task_list']:>9}{c['blind_matched_original']:>18}"
              f"{differed:>10}{c['kept_after_review']:>7}"
              f"{c['changed']:>6} {pct(c['changed'], c['in_task_list']):>4}")
    print()

    # ---- why labels changed ----------------------------------------------
    print("=" * 72)
    print("REASONS GIVEN FOR A CHANGE")
    print("=" * 72)
    reasons = Counter()
    reasons_by_group = {relabel.SOURCE_QUEUE: Counter(), relabel.SOURCE_CONTROL: Counter()}
    for review_id, decision in decisions.items():
        if decision.get("action") != "change":
            continue
        code = decision.get("reason_code") or "unspecified"
        reasons[code] += 1
        group = source_of.get(review_id)
        if group in reasons_by_group:
            reasons_by_group[group][code] += 1

    if reasons:
        print(f"{'reason':<28}{'total':>7}{'queue':>8}{'control':>9}")
        for code, count in reasons.most_common():
            label = relabel.CHANGE_REASONS.get(code, code)
            print(f"{label:<28}{count:>7}"
                  f"{reasons_by_group[relabel.SOURCE_QUEUE][code]:>8}"
                  f"{reasons_by_group[relabel.SOURCE_CONTROL][code]:>9}")
        print(f"{'TOTAL':<28}{sum(reasons.values()):>7}")
    else:
        print("no changes recorded")
    print()

    # ---- what the changes did to the labels ------------------------------
    moves = Counter()
    severity_only = 0
    for review_id, decision in decisions.items():
        if decision.get("action") != "change":
            continue
        old = tuple(sorted(decision.get("old_categories") or []))
        new = tuple(sorted(decision.get("new_categories") or []))
        if old == new:
            severity_only += 1
        else:
            moves[(", ".join(old), ", ".join(new))] += 1
    if moves:
        print("=" * 72)
        print("CATEGORY MOVES")
        print("=" * 72)
        for (old, new), count in moves.most_common():
            print(f"  {count:>2}x  {old:<42} -> {new}")
        if severity_only:
            print(f"  {severity_only:>2}x  (categories unchanged, severity only)")
        print()

    # ---- write the corrected answer key ----------------------------------
    corrected_rows, applied = corrections_module.apply_to_rows(
        gold_rows, corrections_module.load_corrections()
    )
    written = write_jsonl(args.out, corrected_rows)
    changed_ids = {c.review_id for c in applied}

    print("=" * 72)
    print("CORRECTED ANSWER KEY")
    print("=" * 72)
    print(f"Wrote {args.out} ({written} rows, {len(changed_ids)} labels changed)")
    print(f"Original {paths.GOLDEN_SET.name} is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
