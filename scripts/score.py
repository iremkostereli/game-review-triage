"""Recompute every metric from the saved runs. No model is called.

    uv run scripts/score.py
    uv run scripts/score.py --runs runs/ --out results/ --no-bootstrap

Reads the hand-made answer key and the committed run outputs, and writes
results/metrics.json plus results/summary.md. Anyone who clones the repo can run
this and get the published numbers back without an API key, a model, or the raw
dataset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import paths, scoring
from triage.jsonl_io import write_json


def fmt(value: Any, width: int = 6) -> str:
    if value is None:
        return "-".rjust(width)
    if isinstance(value, float):
        return f"{value:.3f}".rjust(width)
    return str(value).rjust(width)


def fmt_delta(entry: dict[str, Any]) -> str:
    if entry.get("delta") is None:
        return "-"
    mark = " *" if entry.get("significant") else ""
    return (
        f"{entry['delta']:+.3f} [{entry['ci_low']:+.3f}, {entry['ci_high']:+.3f}]{mark}"
    )


METRIC_LABELS = {
    "category_micro.f1": "Category micro-F1",
    "category_macro_f1": "Category macro-F1",
    "exact_set_match": "Exact label-set match",
    "issue_detection.f1": "Issue vs no_issue F1",
    "severity.accuracy": "Severity accuracy",
    "high_star_issue_recall.recall": "Issue recall on 4-5 star reviews",
    "jargon_flag_agreement": "Jargon-flag agreement",
}

SLICE_LABELS = {
    "all": "All scored reviews",
    "jargon": "Jargon slice (annotator flag)",
    "no_jargon": "Non-jargon slice",
    "slice_random": "Random slice",
    "slice_enriched": "Enriched slice",
    "stars_1_3": "1-3 star reviews",
    "stars_4_5": "4-5 star reviews",
}


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    gold = report["gold"]
    runs = report["runs"]

    lines.append("# Eval results")
    lines.append("")
    lines.append(
        f"Computed offline from {runs['total']} saved runs over "
        f"{gold['reviews']} hand-labeled reviews "
        f"({', '.join(f'{k} {v}' for k, v in gold['games'].items())}). "
        f"{gold['jargon_flagged']} reviews are flagged as containing jargon by the "
        "annotator."
    )
    lines.append("")
    lines.append(
        "Runs per condition: "
        + ", ".join(f"pack {k.upper()} {v}" for k, v in runs["by_condition"].items())
        + "."
    )
    lines.append("")

    comparison = report.get("comparison") or {}
    if comparison:
        lines.append("## Pack OFF vs ON")
        lines.append("")
        lines.append(
            "Each cell is the ON minus OFF difference with a 95% paired bootstrap "
            "interval over reviews. `*` marks an interval that excludes zero. The "
            "statistic is the mean across repeat runs."
        )
        lines.append("")
        header = "| Slice | n | " + " | ".join(
            METRIC_LABELS[m] for m in scoring.HEADLINE_METRICS
        ) + " |"
        lines.append(header)
        lines.append("|" + "---|" * (len(scoring.HEADLINE_METRICS) + 2))
        for slice_name in SLICE_LABELS:
            if slice_name not in comparison:
                continue
            entries = comparison[slice_name]
            first = entries[scoring.HEADLINE_METRICS[0]]
            cells = [fmt_delta(entries[m]) for m in scoring.HEADLINE_METRICS]
            lines.append(
                f"| {SLICE_LABELS[slice_name]} | {first.get('n', 0)} | "
                + " | ".join(cells)
                + " |"
            )
        lines.append("")

    lines.append("## Absolute scores and run-to-run variance")
    lines.append("")
    for mode, slices in sorted(report["variance"].items()):
        lines.append(f"### Pack {mode.upper()}")
        lines.append("")
        lines.append("| Slice | " + " | ".join(
            METRIC_LABELS[m] for m in scoring.HEADLINE_METRICS
        ) + " |")
        lines.append("|" + "---|" * (len(scoring.HEADLINE_METRICS) + 1))
        for slice_name in SLICE_LABELS:
            if slice_name not in slices:
                continue
            cells = []
            for metric in scoring.HEADLINE_METRICS:
                agg = slices[slice_name][metric]
                if agg["mean"] is None:
                    cells.append("-")
                elif agg["runs"] > 1:
                    cells.append(f"{agg['mean']:.3f} ± {agg['stdev']:.3f}")
                else:
                    cells.append(f"{agg['mean']:.3f}")
            lines.append(f"| {SLICE_LABELS[slice_name]} | " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("## Per-category F1, by condition")
    lines.append("")
    for detail in runs["detail"][:1]:
        support = detail["scores"]["all"].get("per_category_support", {})
        if support:
            lines.append("Support (gold occurrences) per category, all scored reviews:")
            lines.append("")
            lines.append("| Category | Gold reviews |")
            lines.append("|---|---|")
            for name, count in sorted(support.items(), key=lambda kv: -kv[1]):
                lines.append(f"| `{name}` | {count} |")
            lines.append("")
            lines.append(
                "Categories with very few gold examples produce per-category numbers "
                "that are anecdote rather than measurement; read them with the support "
                "column in hand."
            )
            lines.append("")

    lines.append("## Reproducing this")
    lines.append("")
    lines.append("```bash")
    lines.append("uv run scripts/score.py")
    lines.append("```")
    lines.append("")
    lines.append(
        "Reads `data/golden/golden_set.jsonl` and `runs/*/output.json`, both committed. "
        "No model, no API key and no raw dataset needed."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=paths.RUNS_DIR)
    parser.add_argument("--out", type=Path, default=paths.RESULTS_DIR)
    parser.add_argument("--no-bootstrap", action="store_true",
                        help="skip confidence intervals (much faster)")
    parser.add_argument("--resamples", type=int, default=scoring.BOOTSTRAP_RESAMPLES)
    args = parser.parse_args()

    gold = scoring.load_gold()
    if not gold:
        raise SystemExit(
            f"no answer key at {paths.GOLDEN_SET}; label the golden set first"
        )

    runs = scoring.load_runs(args.runs)
    if not runs:
        raise SystemExit(
            f"no complete runs under {args.runs}; run scripts/run_eval.py first"
        )

    print(f"Answer key: {len(gold)} reviews, {sum(1 for g in gold.values() if g.has_jargon)} "
          "flagged as jargon")
    for run in runs:
        print(f"  pack {run.pack_mode} repeat {run.repeat}: {len(run.predictions)} "
              f"predictions from {len(run.batches)} batch(es) over "
              f"{len(run.games)} game(s)")

    report = scoring.build_report(
        gold, runs, bootstrap=not args.no_bootstrap, resamples=args.resamples
    )

    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "metrics.json", report)
    (args.out / "summary.md").write_text(
        render_markdown(report), encoding="utf-8", newline="\n"
    )

    print()
    for mode, slices in sorted(report["variance"].items()):
        agg = slices["all"]["category_micro.f1"]
        jargon = slices["jargon"]["category_micro.f1"]
        print(f"pack {mode.upper():<3} micro-F1 all={fmt(agg['mean'])} "
              f"jargon slice={fmt(jargon['mean'])}")
    if report.get("comparison"):
        for slice_name in ("all", "jargon", "no_jargon"):
            entry = report["comparison"].get(slice_name, {}).get("category_micro.f1")
            if entry and entry.get("delta") is not None:
                print(f"delta micro-F1 on {slice_name:<10} n={entry['n']:<4} "
                      f"{fmt_delta(entry)}")

    print(f"\nWrote {args.out / 'metrics.json'}")
    print(f"Wrote {args.out / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
