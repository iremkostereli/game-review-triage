"""Offline scoring of saved eval runs.

No model is called here, and nothing in this module reaches the network. It reads
the hand-made answer key, reads whatever runs are on disk, and recomputes every
number, so anyone who clones the repo can reproduce the published results from
the committed artifacts alone.

Two deliberate choices:

* **The jargon slice is defined by the annotator's `has_jargon` flag**, never by
  the keyword heuristic that chose which reviews to label. The heuristic exists
  only in `triage/sampling_terms.py` and plays no part in any result.

* **Confidence intervals come from a paired bootstrap over reviews.** The
  headline is a difference between two conditions measured on the *same*
  reviews, so resampling reviews (not runs) and keeping the pairing is what
  reflects the real uncertainty. With a jargon slice of roughly seventy reviews
  the interval is wide, and saying so is the point.
"""

from __future__ import annotations

import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from triage import paths
from triage.jsonl_io import read_json, read_jsonl
from triage.taxonomy import NO_ISSUE, get_taxonomy

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}

#: Fixed so a published interval can be reproduced exactly.
BOOTSTRAP_SEED = 20260214
BOOTSTRAP_RESAMPLES = 2000


@dataclass(frozen=True)
class GoldReview:
    review_id: str
    game: str
    score: int
    categories: frozenset[str]
    severity: str | None
    has_jargon: bool
    slice_name: str

    @property
    def has_issue(self) -> bool:
        return NO_ISSUE not in self.categories


@dataclass(frozen=True)
class Prediction:
    review_id: str
    categories: frozenset[str]
    severity: str | None
    has_jargon: bool

    @property
    def has_issue(self) -> bool:
        return NO_ISSUE not in self.categories


@dataclass(frozen=True)
class Run:
    """One (condition, repeat) worth of predictions, merged over games and batches.

    A repeat spans both games, so a run has to as well: the headline comparison is
    paired per review across conditions, and keeping the games in separate runs
    would leave no review present in every run and silently produce an empty
    interval. Per-game numbers come from the game slices instead.
    """

    pack_mode: str
    repeat: int
    predictions: dict[str, Prediction]
    batches: tuple[str, ...]
    games: tuple[str, ...]


def load_gold(
    golden_set: Path | None = None,
    slices_path: Path | None = None,
    excluded_path: Path | None = None,
    corrections_path: Path | None = None,
) -> dict[str, GoldReview]:
    """The answer key, minus the reviews withheld from eval runs.

    With `corrections_path`, annotator corrections are applied on the way in. The
    file on disk is never modified, so the original and corrected answer keys can
    both be scored from the same committed artifacts.
    """
    golden_set = golden_set or paths.GOLDEN_SET
    slices_path = slices_path or paths.GOLDEN_SLICES
    excluded_path = excluded_path or paths.EXCLUDED_REVIEWS

    slices: dict[str, str] = {}
    if slices_path.exists():
        slices = read_json(slices_path).get("slices", {})

    withheld: set[str] = set()
    if excluded_path.exists():
        withheld = {item["reviewId"] for item in read_json(excluded_path).get("excluded", [])}

    rows = read_jsonl(golden_set)
    if corrections_path is not None:
        from triage import corrections as corrections_module

        rows, _ = corrections_module.apply_to_rows(
            rows, corrections_module.load_corrections(corrections_path)
        )

    gold: dict[str, GoldReview] = {}
    for row in rows:
        review_id = row["reviewId"]
        if review_id in withheld:
            continue
        gold[review_id] = GoldReview(
            review_id=review_id,
            game=row["game"],
            score=int(row["score"]),
            categories=frozenset(row["categories"]),
            severity=row.get("severity") or None,
            has_jargon=bool(row.get("has_jargon")),
            slice_name=slices.get(review_id, "unknown"),
        )
    return gold


def load_runs(runs_dir: Path | None = None) -> list[Run]:
    """Merge every complete batch on disk into one Run per (condition, repeat)."""
    runs_dir = runs_dir or paths.RUNS_DIR
    if not runs_dir.exists():
        return []

    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    for meta_path in sorted(runs_dir.glob("*/meta.json")):
        meta = read_json(meta_path)
        if meta.get("status") != "ok":
            continue
        output_path = meta_path.parent / "output.json"
        if not output_path.exists():
            continue

        key = (meta["pack_mode"], int(meta["repeat"]))
        bucket = grouped.setdefault(key, {"predictions": {}, "batches": [], "games": set()})
        bucket["batches"].append(meta["run_id"])
        bucket["games"].add(meta["game"])

        for result in read_json(output_path).get("results", []):
            review_id = result.get("reviewId")
            if not review_id:
                continue
            bucket["predictions"][review_id] = Prediction(
                review_id=review_id,
                categories=frozenset(result.get("categories") or []),
                severity=(result.get("severity") or None),
                has_jargon=bool(result.get("has_jargon")),
            )

    return [
        Run(
            pack_mode=mode,
            repeat=repeat,
            predictions=bucket["predictions"],
            batches=tuple(sorted(bucket["batches"])),
            games=tuple(sorted(bucket["games"])),
        )
        for (mode, repeat), bucket in sorted(grouped.items())
    ]


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def _prf(true_positive: int, false_positive: int, false_negative: int) -> dict[str, float]:
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def score_pairs(
    pairs: Sequence[tuple[GoldReview, Prediction]],
    categories: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Every metric, for one set of matched (gold, prediction) pairs."""
    if not pairs:
        return {"n": 0}

    categories = list(categories if categories is not None else get_taxonomy().category_ids)

    micro_tp = micro_fp = micro_fn = 0
    per_category: dict[str, dict[str, int]] = {
        name: {"tp": 0, "fp": 0, "fn": 0} for name in categories
    }
    exact = 0

    severity_total = severity_exact = severity_within_one = 0
    jargon_agree = 0
    high_star_total = high_star_recalled = 0
    issue_tp = issue_fp = issue_fn = 0

    for gold, pred in pairs:
        if gold.categories == pred.categories:
            exact += 1
        for name in categories:
            in_gold = name in gold.categories
            in_pred = name in pred.categories
            if in_gold and in_pred:
                per_category[name]["tp"] += 1
                micro_tp += 1
            elif in_pred:
                per_category[name]["fp"] += 1
                micro_fp += 1
            elif in_gold:
                per_category[name]["fn"] += 1
                micro_fn += 1

        # Severity is only defined where the annotator rated an issue.
        if gold.severity:
            severity_total += 1
            if pred.severity == gold.severity:
                severity_exact += 1
            if pred.severity in SEVERITY_RANK and abs(
                SEVERITY_RANK[pred.severity] - SEVERITY_RANK[gold.severity]
            ) <= 1:
                severity_within_one += 1

        if gold.has_jargon == pred.has_jargon:
            jargon_agree += 1

        # "Do not trust the stars": of the 4-5 star reviews that really do carry
        # an issue, how many did the system call an issue?
        if gold.score >= 4 and gold.has_issue:
            high_star_total += 1
            if pred.has_issue:
                high_star_recalled += 1

        if gold.has_issue and pred.has_issue:
            issue_tp += 1
        elif pred.has_issue and not gold.has_issue:
            issue_fp += 1
        elif gold.has_issue and not pred.has_issue:
            issue_fn += 1

    macro = [
        _prf(c["tp"], c["fp"], c["fn"])["f1"]
        for c in per_category.values()
        if c["tp"] + c["fn"] > 0  # categories absent from the gold are not averaged
    ]

    return {
        "n": len(pairs),
        "category_micro": _prf(micro_tp, micro_fp, micro_fn),
        "category_macro_f1": round(statistics.fmean(macro), 4) if macro else 0.0,
        "exact_set_match": round(exact / len(pairs), 4),
        "severity": {
            "n": severity_total,
            "accuracy": round(severity_exact / severity_total, 4) if severity_total else None,
            "within_one": round(severity_within_one / severity_total, 4) if severity_total else None,
        },
        "issue_detection": _prf(issue_tp, issue_fp, issue_fn),
        "high_star_issue_recall": {
            "n": high_star_total,
            "recall": round(high_star_recalled / high_star_total, 4) if high_star_total else None,
        },
        "jargon_flag_agreement": round(jargon_agree / len(pairs), 4),
        "per_category_f1": {
            name: _prf(c["tp"], c["fp"], c["fn"])["f1"]
            for name, c in per_category.items()
            if c["tp"] + c["fn"] > 0
        },
        "per_category_support": {
            name: c["tp"] + c["fn"] for name, c in per_category.items() if c["tp"] + c["fn"] > 0
        },
    }


def match(gold: dict[str, GoldReview], run: Run) -> list[tuple[GoldReview, Prediction]]:
    """Pairs for the reviews this run actually triaged, in a stable order."""
    return [
        (gold[rid], run.predictions[rid])
        for rid in sorted(run.predictions)
        if rid in gold
    ]


# --------------------------------------------------------------------------
# Slices
# --------------------------------------------------------------------------

SliceFn = Callable[[GoldReview], bool]


def all_category_ids() -> tuple[str, ...]:
    return get_taxonomy().category_ids


def slice_definitions(games: Iterable[str]) -> dict[str, SliceFn]:
    """The breakdowns the README reports."""
    slices: dict[str, SliceFn] = {
        "all": lambda g: True,
        "jargon": lambda g: g.has_jargon,
        "no_jargon": lambda g: not g.has_jargon,
        "slice_random": lambda g: g.slice_name == "random",
        "slice_enriched": lambda g: g.slice_name == "enriched",
        "stars_1_3": lambda g: g.score <= 3,
        "stars_4_5": lambda g: g.score >= 4,
    }
    for game in games:
        slices[f"game_{game}"] = (lambda name: (lambda g: g.game == name))(game)
    return slices


def score_run_by_slice(
    gold: dict[str, GoldReview], run: Run, slices: dict[str, SliceFn]
) -> dict[str, Any]:
    pairs = match(gold, run)
    return {
        name: score_pairs([p for p in pairs if keep(p[0])])
        for name, keep in slices.items()
    }


# --------------------------------------------------------------------------
# Aggregation across repeats, and the paired bootstrap
# --------------------------------------------------------------------------


def _pluck(scored: dict[str, Any], metric: str) -> float | None:
    """Read a metric out of a score dict by dotted path."""
    node: Any = scored
    for part in metric.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, (int, float)) else None


def aggregate_repeats(per_repeat: Sequence[dict[str, Any]], metric: str) -> dict[str, Any]:
    """Mean and spread of one metric across repeat runs."""
    values = [v for v in (_pluck(s, metric) for s in per_repeat) if v is not None]
    if not values:
        return {"runs": 0, "mean": None, "stdev": None, "values": []}
    return {
        "runs": len(values),
        "mean": round(statistics.fmean(values), 4),
        "stdev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "values": [round(v, 4) for v in values],
    }


def paired_bootstrap_delta(
    gold: dict[str, GoldReview],
    runs_off: Sequence[Run],
    runs_on: Sequence[Run],
    metric: str,
    keep: SliceFn,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """A confidence interval for the ON minus OFF difference on one slice.

    Reviews are the sampling unit and the pairing is preserved: each resample
    draws review ids, then recomputes the metric for both conditions on exactly
    those ids. The statistic is the mean across repeat runs, so run-to-run
    variance is inside the estimate rather than hidden by it.
    """
    shared = sorted(
        rid
        for rid in gold
        if keep(gold[rid])
        and all(rid in run.predictions for run in runs_off)
        and all(rid in run.predictions for run in runs_on)
    )
    if not shared or not runs_off or not runs_on:
        return {"n": len(shared), "delta": None, "ci_low": None, "ci_high": None}

    categories = all_category_ids()

    def statistic(ids: Sequence[str], runs: Sequence[Run]) -> float | None:
        values = []
        for run in runs:
            pairs = [(gold[rid], run.predictions[rid]) for rid in ids]
            value = _pluck(score_pairs(pairs, categories), metric)
            if value is not None:
                values.append(value)
        return statistics.fmean(values) if values else None

    observed_off = statistic(shared, runs_off)
    observed_on = statistic(shared, runs_on)
    if observed_off is None or observed_on is None:
        return {"n": len(shared), "delta": None, "ci_low": None, "ci_high": None}

    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(resamples):
        sample = [shared[rng.randrange(len(shared))] for _ in range(len(shared))]
        off = statistic(sample, runs_off)
        on = statistic(sample, runs_on)
        if off is not None and on is not None:
            deltas.append(on - off)

    deltas.sort()
    low = deltas[int(0.025 * len(deltas))] if deltas else None
    high = deltas[int(0.975 * len(deltas)) - 1] if deltas else None
    return {
        "n": len(shared),
        "metric": metric,
        "off": round(observed_off, 4),
        "on": round(observed_on, 4),
        "delta": round(observed_on - observed_off, 4),
        "ci_low": round(low, 4) if low is not None else None,
        "ci_high": round(high, 4) if high is not None else None,
        "resamples": len(deltas),
        "significant": (
            bool(low is not None and high is not None and (low > 0 or high < 0))
        ),
    }


def paired_bootstrap_all(
    gold: dict[str, GoldReview],
    runs_off: Sequence[Run],
    runs_on: Sequence[Run],
    keep: SliceFn,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Every headline metric's ON-minus-OFF interval, from one set of resamples.

    Scoring once per resample and reading all metrics off that result keeps the
    cost linear in resamples rather than in resamples times metrics, and means
    every interval is drawn from the same resamples.
    """
    shared = sorted(
        rid
        for rid in gold
        if keep(gold[rid])
        and all(rid in run.predictions for run in runs_off)
        and all(rid in run.predictions for run in runs_on)
    )
    empty = {
        metric: {"n": len(shared), "metric": metric, "delta": None,
                 "ci_low": None, "ci_high": None}
        for metric in HEADLINE_METRICS
    }
    if not shared or not runs_off or not runs_on:
        return empty

    categories = all_category_ids()

    def scores(ids: Sequence[str], runs: Sequence[Run]) -> dict[str, float]:
        """Mean of each metric across repeat runs, on these review ids."""
        collected: dict[str, list[float]] = defaultdict(list)
        for run in runs:
            scored = score_pairs([(gold[rid], run.predictions[rid]) for rid in ids], categories)
            for metric in HEADLINE_METRICS:
                value = _pluck(scored, metric)
                if value is not None:
                    collected[metric].append(value)
        return {m: statistics.fmean(v) for m, v in collected.items() if v}

    observed_off = scores(shared, runs_off)
    observed_on = scores(shared, runs_on)

    rng = random.Random(seed)
    draws: dict[str, list[float]] = defaultdict(list)
    for _ in range(resamples):
        sample = [shared[rng.randrange(len(shared))] for _ in range(len(shared))]
        off = scores(sample, runs_off)
        on = scores(sample, runs_on)
        for metric in HEADLINE_METRICS:
            if metric in off and metric in on:
                draws[metric].append(on[metric] - off[metric])

    result: dict[str, Any] = {}
    for metric in HEADLINE_METRICS:
        values = sorted(draws.get(metric, []))
        if metric not in observed_off or metric not in observed_on or not values:
            result[metric] = empty[metric]
            continue
        low = values[int(0.025 * len(values))]
        high = values[int(0.975 * len(values)) - 1]
        result[metric] = {
            "n": len(shared),
            "metric": metric,
            "off": round(observed_off[metric], 4),
            "on": round(observed_on[metric], 4),
            "delta": round(observed_on[metric] - observed_off[metric], 4),
            "ci_low": round(low, 4),
            "ci_high": round(high, 4),
            "resamples": len(values),
            "significant": bool(low > 0 or high < 0),
        }
    return result


# --------------------------------------------------------------------------
# Top-level report
# --------------------------------------------------------------------------

#: Metrics carried into the OFF/ON comparison table.
HEADLINE_METRICS = (
    "category_micro.f1",
    "category_macro_f1",
    "exact_set_match",
    "issue_detection.f1",
    "severity.accuracy",
    "high_star_issue_recall.recall",
    "jargon_flag_agreement",
)


def build_report(
    gold: dict[str, GoldReview],
    runs: Sequence[Run],
    bootstrap: bool = True,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Everything the report needs, computed from the answer key and saved runs."""
    games = sorted({g.game for g in gold.values()})
    slices = slice_definitions(games)

    by_condition: dict[str, list[Run]] = defaultdict(list)
    for run in runs:
        by_condition[run.pack_mode].append(run)

    per_run = [
        {
            "games": list(run.games),
            "pack_mode": run.pack_mode,
            "repeat": run.repeat,
            "batches": list(run.batches),
            "reviews_scored": len(match(gold, run)),
            "scores": score_run_by_slice(gold, run, slices),
        }
        for run in runs
    ]

    variance: dict[str, Any] = {}
    for mode, mode_runs in sorted(by_condition.items()):
        scored = [score_run_by_slice(gold, run, slices) for run in mode_runs]
        variance[mode] = {
            slice_name: {
                metric: aggregate_repeats([s[slice_name] for s in scored], metric)
                for metric in HEADLINE_METRICS
            }
            for slice_name in slices
        }

    comparison: dict[str, Any] = {}
    if bootstrap and by_condition.get("off") and by_condition.get("on"):
        for slice_name, keep in slices.items():
            comparison[slice_name] = paired_bootstrap_all(
                gold,
                by_condition["off"],
                by_condition["on"],
                keep,
                resamples=resamples,
            )

    return {
        "gold": {
            "reviews": len(gold),
            "games": {game: sum(1 for g in gold.values() if g.game == game) for game in games},
            "jargon_flagged": sum(1 for g in gold.values() if g.has_jargon),
            "slices": {
                name: sum(1 for g in gold.values() if keep(g)) for name, keep in slices.items()
            },
        },
        "runs": {
            "total": len(runs),
            "by_condition": {mode: len(rs) for mode, rs in sorted(by_condition.items())},
            "detail": per_run,
        },
        "variance": variance,
        "comparison": comparison,
    }
