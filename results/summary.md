# Eval results

Computed offline from 6 saved runs over 178 hand-labeled reviews (Candy Crush Saga 79, Clash of Clans 99). 71 reviews are flagged as containing jargon by the annotator.

Runs per condition: pack OFF 3, pack ON 3.

## Pack OFF vs ON

Each cell is the ON minus OFF difference with a 95% paired bootstrap interval over reviews. `*` marks an interval that excludes zero. The statistic is the mean across repeat runs.

| Slice | n | Category micro-F1 | Category macro-F1 | Exact label-set match | Issue vs no_issue F1 | Severity accuracy | Issue recall on 4-5 star reviews | Jargon-flag agreement |
|---|---|---|---|---|---|---|---|---|
| All scored reviews | 178 | +0.000 [-0.014, +0.015] | -0.005 [-0.021, +0.011] | +0.004 [-0.017, +0.026] | +0.003 [+0.000, +0.007] | -0.000 [-0.021, +0.019] | +0.000 [+0.000, +0.000] | -0.051 [-0.090, -0.015] * |
| Jargon slice (annotator flag) | 71 | -0.006 [-0.032, +0.019] | -0.010 [-0.042, +0.018] | -0.000 [-0.047, +0.047] | +0.000 [+0.000, +0.000] | -0.006 [-0.037, +0.023] | +0.000 [+0.000, +0.000] | +0.014 [-0.014, +0.042] |
| Non-jargon slice | 107 | +0.004 [-0.011, +0.022] | +0.000 [-0.018, +0.021] | +0.006 [-0.012, +0.022] | +0.005 [+0.000, +0.014] | +0.005 [-0.021, +0.033] | +0.000 [+0.000, +0.000] | -0.093 [-0.153, -0.037] * |
| Random slice | 58 | -0.006 [-0.027, +0.013] | -0.032 [-0.064, +0.002] | +0.006 [-0.011, +0.023] | +0.011 [+0.000, +0.028] | -0.011 [-0.049, +0.025] | +0.000 [+0.000, +0.000] | -0.058 [-0.121, -0.011] * |
| Enriched slice | 120 | +0.003 [-0.014, +0.023] | -0.005 [-0.023, +0.013] | +0.003 [-0.028, +0.033] | +0.000 [+0.000, +0.000] | +0.004 [-0.021, +0.027] | +0.000 [+0.000, +0.000] | -0.047 [-0.100, +0.000] |
| 1-3 star reviews | 83 | -0.008 [-0.031, +0.015] | +0.001 [-0.042, +0.024] | -0.004 [-0.048, +0.036] | +0.002 [+0.000, +0.006] | +0.008 [-0.013, +0.029] | - | -0.088 [-0.153, -0.032] * |
| 4-5 star reviews | 95 | +0.009 [-0.006, +0.027] | +0.004 [-0.019, +0.031] | +0.011 [-0.004, +0.032] | +0.004 [+0.000, +0.012] | -0.016 [-0.059, +0.017] | +0.000 [+0.000, +0.000] | -0.018 [-0.067, +0.028] |

## Absolute scores and run-to-run variance

### Pack OFF

| Slice | Category micro-F1 | Category macro-F1 | Exact label-set match | Issue vs no_issue F1 | Severity accuracy | Issue recall on 4-5 star reviews | Jargon-flag agreement |
|---|---|---|---|---|---|---|---|
| All scored reviews | 0.792 ± 0.013 | 0.713 ± 0.014 | 0.712 ± 0.023 | 0.987 ± 0.006 | 0.707 ± 0.014 | 1.000 ± 0.000 | 0.875 ± 0.020 |
| Jargon slice (annotator flag) | 0.777 ± 0.017 | 0.710 ± 0.014 | 0.681 ± 0.021 | 0.983 ± 0.000 | 0.678 ± 0.034 | 1.000 ± 0.000 | 0.883 ± 0.016 |
| Non-jargon slice | 0.803 ± 0.016 | 0.693 ± 0.012 | 0.732 ± 0.024 | 0.990 ± 0.012 | 0.734 ± 0.016 | 1.000 ± 0.000 | 0.869 ± 0.034 |
| Random slice | 0.827 ± 0.018 | 0.730 ± 0.007 | 0.782 ± 0.020 | 0.989 ± 0.019 | 0.645 ± 0.000 | 1.000 ± 0.000 | 0.925 ± 0.020 |
| Enriched slice | 0.777 ± 0.013 | 0.687 ± 0.013 | 0.678 ± 0.027 | 0.986 ± 0.003 | 0.728 ± 0.019 | 1.000 ± 0.000 | 0.850 ± 0.022 |
| 1-3 star reviews | 0.772 ± 0.006 | 0.753 ± 0.024 | 0.626 ± 0.024 | 0.998 ± 0.004 | 0.658 ± 0.012 | - | 0.839 ± 0.030 |
| 4-5 star reviews | 0.813 ± 0.021 | 0.638 ± 0.013 | 0.786 ± 0.022 | 0.965 ± 0.011 | 0.805 ± 0.024 | 1.000 ± 0.000 | 0.905 ± 0.011 |

### Pack ON

| Slice | Category micro-F1 | Category macro-F1 | Exact label-set match | Issue vs no_issue F1 | Severity accuracy | Issue recall on 4-5 star reviews | Jargon-flag agreement |
|---|---|---|---|---|---|---|---|
| All scored reviews | 0.792 ± 0.008 | 0.709 ± 0.004 | 0.715 ± 0.013 | 0.989 ± 0.002 | 0.707 ± 0.008 | 1.000 ± 0.000 | 0.824 ± 0.017 |
| Jargon slice (annotator flag) | 0.770 ± 0.005 | 0.699 ± 0.006 | 0.681 ± 0.016 | 0.983 ± 0.000 | 0.672 ± 0.026 | 1.000 ± 0.000 | 0.897 ± 0.021 |
| Non-jargon slice | 0.807 ± 0.016 | 0.693 ± 0.014 | 0.738 ± 0.019 | 0.995 ± 0.004 | 0.740 ± 0.009 | 1.000 ± 0.000 | 0.776 ± 0.016 |
| Random slice | 0.821 ± 0.019 | 0.698 ± 0.027 | 0.787 ± 0.020 | 1.000 ± 0.000 | 0.634 ± 0.019 | 1.000 ± 0.000 | 0.868 ± 0.010 |
| Enriched slice | 0.779 ± 0.005 | 0.682 ± 0.001 | 0.681 ± 0.010 | 0.986 ± 0.003 | 0.732 ± 0.013 | 1.000 ± 0.000 | 0.803 ± 0.021 |
| 1-3 star reviews | 0.764 ± 0.013 | 0.754 ± 0.008 | 0.623 ± 0.025 | 1.000 ± 0.000 | 0.667 ± 0.007 | - | 0.751 ± 0.018 |
| 4-5 star reviews | 0.822 ± 0.005 | 0.642 ± 0.002 | 0.796 ± 0.006 | 0.969 ± 0.007 | 0.789 ± 0.014 | 1.000 ± 0.000 | 0.888 ± 0.016 |

## Per-category F1, by condition

Support (gold occurrences) per category, all scored reviews:

| Category | Gold reviews |
|---|---|
| `no_issue` | 55 |
| `content_ux` | 43 |
| `difficulty_balance` | 37 |
| `monetization` | 17 |
| `stability_performance` | 15 |
| `account_progress_loss` | 14 |
| `ads` | 12 |
| `other_issue` | 6 |

Categories with very few gold examples produce per-category numbers that are anecdote rather than measurement; read them with the support column in hand.

## Reproducing this

```bash
uv run scripts/score.py
```

Reads `data/golden/golden_set.jsonl` and `runs/*/output.json`, both committed. No model, no API key and no raw dataset needed.
