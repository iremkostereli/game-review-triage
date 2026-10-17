"""List the reviews where every run disagreed with the answer key, the same way.

    uv run scripts/label_review_queue.py --out data/golden/label_review_queue.md

When all six runs (both conditions, three repeats each) independently produce the
same label set and it differs from the hand-made label, that is worth a second
look by the annotator. Unanimity across conditions matters: a disagreement that
survives with the jargon pack on and off is unlikely to be a vocabulary problem.

**This queue is a review aid, not a verdict.** It is selected by the system's own
output, so it can only ever point at labels where the system differs from the
annotator - never at labels where the system agrees but is wrong. Any correction
made from it moves the answer key towards the system by construction. That is why
`scripts/score.py` keeps scoring the original set as well, and why the README has
to report both numbers side by side.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import corrections, paths, scoring
from triage.jsonl_io import read_json, read_jsonl


def collect_predictions(runs_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """reviewId -> one entry per completed run, with its own rationale."""
    per_review: dict[str, list[dict[str, Any]]] = defaultdict(list)
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
            per_review[review_id].append(
                {
                    "pack_mode": meta["pack_mode"],
                    "repeat": meta["repeat"],
                    "categories": tuple(sorted(result.get("categories") or [])),
                    "severity": result.get("severity"),
                    "rationale": (result.get("rationale") or "").strip(),
                }
            )
    return per_review


def find_unanimous_disagreements(
    gold: dict[str, scoring.GoldReview],
    per_review: dict[str, list[dict[str, Any]]],
    expected_runs: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Two lists: category disagreements, and severity-only disagreements."""
    category_rows: list[dict[str, Any]] = []
    severity_rows: list[dict[str, Any]] = []

    for review_id, entries in per_review.items():
        if review_id not in gold or len(entries) < expected_runs:
            continue

        category_sets = {entry["categories"] for entry in entries}
        severities = {entry["severity"] for entry in entries}
        gold_review = gold[review_id]
        gold_categories = tuple(sorted(gold_review.categories))

        if len(category_sets) != 1:
            continue  # the runs disagree with each other, so not a clean signal
        model_categories = next(iter(category_sets))

        rationales = []
        for entry in entries:
            if entry["rationale"] and entry["rationale"] not in rationales:
                rationales.append(entry["rationale"])

        row = {
            "reviewId": review_id,
            "game": gold_review.game,
            "score": gold_review.score,
            "gold_categories": list(gold_categories),
            "gold_severity": gold_review.severity,
            "gold_has_jargon": gold_review.has_jargon,
            "model_categories": list(model_categories),
            "model_severity": next(iter(severities)) if len(severities) == 1 else None,
            "model_severities": sorted(s for s in severities if s),
            "rationales": rationales[:3],
            "runs": len(entries),
        }

        if model_categories != gold_categories:
            category_rows.append(row)
        elif len(severities) == 1 and next(iter(severities)) != gold_review.severity:
            severity_rows.append(row)

    category_rows.sort(key=lambda r: (r["gold_categories"], r["game"], r["reviewId"]))
    severity_rows.sort(key=lambda r: (str(r["gold_severity"]), r["game"], r["reviewId"]))
    return category_rows, severity_rows


def render(
    category_rows: list[dict[str, Any]],
    severity_rows: list[dict[str, Any]],
    text: dict[str, str],
    total_scored: int,
    expected_runs: int,
) -> str:
    lines: list[str] = []
    lines.append("# Label review queue")
    lines.append("")
    lines.append(
        f"Reviews where all {expected_runs} runs (pack off and on, three repeats each) "
        f"produced the *same* labels, and those labels differ from the answer key. "
        f"{len(category_rows)} category disagreements and {len(severity_rows)} "
        f"severity-only disagreements, out of {total_scored} scored reviews."
    )
    lines.append("")
    lines.append(
        "**Read this as a list of labels worth re-checking against "
        "`docs/LABELING_GUIDE.md`, not as a list of mistakes.** The queue is "
        "selected by the system's own output, so it can only point at places where "
        "the system differs from you. It cannot show you labels where the system "
        "agreed with you and both were wrong. Correcting from it therefore moves the "
        "answer key towards the system by construction, which is why the results are "
        "reported against both the original and the corrected set."
    )
    lines.append("")
    lines.append(
        "To change a label, add a line to `data/golden/corrections.jsonl`. "
        "Leaving a review out means the original label stands."
    )
    lines.append("")

    def block(row: dict[str, Any]) -> list[str]:
        out = []
        jargon = " · jargon" if row["gold_has_jargon"] else ""
        out.append(f"#### `{row['reviewId']}`")
        out.append("")
        out.append(f"*{row['game']} · {row['score']} stars{jargon}*")
        out.append("")
        out.append("> " + (text.get(row["reviewId"], "").replace("\n", " ")))
        out.append("")
        out.append(
            f"- **Your label:** `{', '.join(row['gold_categories'])}`"
            + (f" · severity `{row['gold_severity']}`" if row["gold_severity"] else "")
        )
        model_sev = row["model_severity"] or ", ".join(row["model_severities"]) or "none"
        out.append(
            f"- **All {row['runs']} runs said:** `{', '.join(row['model_categories'])}`"
            f" · severity `{model_sev}`"
        )
        out.append("- **Its reasoning:**")
        for rationale in row["rationales"]:
            out.append(f"  - {rationale}")
        out.append("")
        return out

    if category_rows:
        lines.append("## Category disagreements, grouped by your label")
        lines.append("")
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in category_rows:
            grouped[", ".join(row["gold_categories"])].append(row)
        for gold_label, rows in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### Your label: `{gold_label}` ({len(rows)} reviews)")
            lines.append("")
            for row in rows:
                lines.extend(block(row))

    if severity_rows:
        lines.append("## Severity-only disagreements")
        lines.append("")
        lines.append("Categories match; only the severity differs.")
        lines.append("")
        grouped_sev: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in severity_rows:
            grouped_sev[str(row["gold_severity"])].append(row)
        for gold_sev, rows in sorted(grouped_sev.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### Your severity: `{gold_sev}` ({len(rows)} reviews)")
            lines.append("")
            for row in rows:
                lines.extend(block(row))

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=paths.RUNS_DIR)
    parser.add_argument("--out", type=Path, default=paths.GOLDEN_DIR / "label_review_queue.md")
    parser.add_argument("--expected-runs", type=int, default=6,
                        help="how many runs must agree before a review is listed")
    parser.add_argument("--scaffold", type=Path,
                        default=paths.GOLDEN_DIR / "corrections.scaffold.jsonl",
                        help="pre-filled corrections file to edit")
    args = parser.parse_args()

    gold = scoring.load_gold()
    text = {row["reviewId"]: row["content"] for row in read_jsonl(paths.GOLDEN_SET)}
    per_review = collect_predictions(args.runs)
    if not per_review:
        raise SystemExit(f"no completed runs under {args.runs}")

    category_rows, severity_rows = find_unanimous_disagreements(
        gold, per_review, args.expected_runs
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render(category_rows, severity_rows, text, len(gold), args.expected_runs),
        encoding="utf-8",
        newline="\n",
    )

    print(f"{len(gold)} scored reviews, {args.expected_runs} runs each")
    print(f"  unanimous category disagreements: {len(category_rows)}")
    print(f"  unanimous severity-only disagreements: {len(severity_rows)}")
    print()
    grouped: dict[str, int] = defaultdict(int)
    for row in category_rows:
        grouped[", ".join(row["gold_categories"])] += 1
    for gold_label, count in sorted(grouped.items(), key=lambda kv: -kv[1]):
        print(f"  your label `{gold_label}`: {count}")
    written = corrections.write_scaffold(args.scaffold, category_rows + severity_rows)

    print(f"\nWrote {args.out}")
    print(f'Wrote {args.scaffold} ({written} candidates, all set to "keep")')
    print()
    print('To change a label: set "action" to "change", edit new_categories and')
    print("new_severity, add a reason, then save the file as")
    print(f"  {paths.GOLDEN_CORRECTIONS.relative_to(paths.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
