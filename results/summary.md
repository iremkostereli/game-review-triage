# Eval results

Computed offline from 2 saved runs over 178 hand-labeled reviews (Candy Crush Saga 79, Clash of Clans 99). 71 reviews are flagged as containing jargon by the annotator.

Runs per condition: pack OFF 1, pack ON 1.

## Pack OFF vs ON

Each cell is the ON minus OFF difference with a 95% paired bootstrap interval over reviews. `*` marks an interval that excludes zero. The statistic is the mean across repeat runs.

| Slice | n | Category micro-F1 | Category macro-F1 | Exact label-set match | Issue vs no_issue F1 | Severity accuracy | Issue recall on 4-5 star reviews | Jargon-flag agreement |
|---|---|---|---|---|---|---|---|---|
| All scored reviews | 40 | -0.004 [-0.038, +0.033] | +0.004 [-0.021, +0.048] | -0.025 [-0.100, +0.050] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | -0.150 [-0.275, -0.050] * |
| Jargon slice (annotator flag) | 13 | +0.017 [-0.067, +0.107] | +0.083 [+0.000, +0.250] | +0.000 [-0.231, +0.231] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | -0.077 [-0.231, +0.000] |
| Non-jargon slice | 27 | -0.013 [-0.043, +0.000] | -0.014 [-0.056, +0.000] | -0.037 [-0.111, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | -0.185 [-0.333, -0.037] * |
| Random slice | 23 | -0.017 [-0.054, +0.000] | -0.014 [-0.056, +0.000] | -0.043 [-0.131, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | -0.087 [-0.217, +0.000] |
| Enriched slice | 17 | +0.013 [-0.051, +0.085] | +0.056 [+0.000, +0.200] | +0.000 [-0.176, +0.176] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | -0.235 [-0.471, -0.059] * |
| 1-3 star reviews | 23 | -0.003 [-0.057, +0.057] | +0.004 [-0.025, +0.056] | -0.043 [-0.174, +0.087] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | - | -0.131 [-0.261, +0.000] |
| 4-5 star reviews | 17 | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | +0.000 [+0.000, +0.000] | -0.176 [-0.353, +0.000] |

## Absolute scores and run-to-run variance

### Pack OFF

| Slice | Category micro-F1 | Category macro-F1 | Exact label-set match | Issue vs no_issue F1 | Severity accuracy | Issue recall on 4-5 star reviews | Jargon-flag agreement |
|---|---|---|---|---|---|---|---|
| All scored reviews | 0.778 | 0.699 | 0.675 | 1.000 | 0.567 | 1.000 | 0.900 |
| Jargon slice (annotator flag) | 0.733 | 0.768 | 0.615 | 1.000 | 0.462 | 1.000 | 1.000 |
| Non-jargon slice | 0.800 | 0.639 | 0.704 | 1.000 | 0.647 | 1.000 | 0.852 |
| Random slice | 0.833 | 0.676 | 0.783 | 1.000 | 0.500 | 1.000 | 0.870 |
| Enriched slice | 0.714 | 0.792 | 0.529 | 1.000 | 0.625 | 1.000 | 0.941 |
| 1-3 star reviews | 0.727 | 0.654 | 0.565 | 1.000 | 0.478 | - | 0.870 |
| 4-5 star reviews | 0.857 | 0.813 | 0.824 | 1.000 | 0.857 | 1.000 | 0.941 |

### Pack ON

| Slice | Category micro-F1 | Category macro-F1 | Exact label-set match | Issue vs no_issue F1 | Severity accuracy | Issue recall on 4-5 star reviews | Jargon-flag agreement |
|---|---|---|---|---|---|---|---|
| All scored reviews | 0.774 | 0.703 | 0.650 | 1.000 | 0.567 | 1.000 | 0.750 |
| Jargon slice (annotator flag) | 0.750 | 0.852 | 0.615 | 1.000 | 0.462 | 1.000 | 0.923 |
| Non-jargon slice | 0.787 | 0.625 | 0.667 | 1.000 | 0.647 | 1.000 | 0.667 |
| Random slice | 0.816 | 0.663 | 0.739 | 1.000 | 0.500 | 1.000 | 0.783 |
| Enriched slice | 0.727 | 0.847 | 0.529 | 1.000 | 0.625 | 1.000 | 0.706 |
| 1-3 star reviews | 0.724 | 0.658 | 0.522 | 1.000 | 0.478 | - | 0.739 |
| 4-5 star reviews | 0.857 | 0.813 | 0.824 | 1.000 | 0.857 | 1.000 | 0.765 |

## Per-category F1, by condition

Support (gold occurrences) per category, all scored reviews:

| Category | Gold reviews |
|---|---|
| `no_issue` | 10 |
| `content_ux` | 9 |
| `stability_performance` | 7 |
| `account_progress_loss` | 7 |
| `difficulty_balance` | 7 |
| `ads` | 4 |
| `other_issue` | 1 |

Categories with very few gold examples produce per-category numbers that are anecdote rather than measurement; read them with the support column in hand.

## Reproducing this

```bash
uv run scripts/score.py
```

Reads `data/golden/golden_set.jsonl` and `runs/*/output.json`, both committed. No model, no API key and no raw dataset needed.
