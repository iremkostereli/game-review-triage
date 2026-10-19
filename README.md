# Game review triage

A Claude Code skill plus an MCP server that turns mobile game app reviews into
actionable LiveOps issues: categories, a severity, and grouped issues with quoted
evidence. It ships pluggable per-game jargon packs and an eval that measures
whether they actually help.

## Headline

- **The triage works.** Against the corrected answer key it reaches 0.873
  category micro-F1 and 0.793 severity accuracy, and it separates an actionable
  issue from praise almost perfectly (0.991 F1).
- **The jargon pack does not change category accuracy on these two games.**
  ON minus OFF is +0.000, 95% interval [-0.014, +0.015] - a measured null, not an
  underpowered one. The pack-off runs already read `town hall`, `builder base` and
  `gold pass` correctly; their mistakes are category choices, not vocabulary.
- **The pack slightly hurts the jargon flag.** Agreement with the annotator's
  hand-set flag falls from 0.875 to 0.824 (-0.051), because ordinary pack terms
  like `moves`, `lives` and `gold` start getting flagged as game jargon.

178 reviews, three repeat runs per condition, `claude-sonnet-5-5` via headless
`claude -p`.

| Metric | Pack OFF | Pack ON |
|---|---|---|
| Category micro-F1 | 0.873 | 0.873 |
| Severity accuracy | 0.793 | 0.790 |
| Issue vs `no_issue` F1 | 0.991 | 0.993 |
| Jargon-flag agreement | 0.875 | 0.824 |

Original (pre-correction) labels: category micro-F1 0.792. Per-slice tables and
confidence intervals are in [`results/summary.md`](results/summary.md).

Data: the Kaggle "game-reviews" dataset
([araraltawil/game-reviews](https://www.kaggle.com/datasets/araraltawil/game-reviews)),
MIT licensed; how to obtain it is in
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Labeling

One annotator labeled all 180 reviews by hand, with no model involved at any
point. A blind second pass relabeled a shuffled mix of 46 reviews where every run
disagreed with the annotator and 30 controls where the runs agreed, with the
group hidden: 1 of the 30 controls changed and 31 of the 46 queued reviews did,
giving 32 corrections. `golden_set.jsonl` was never modified, and both answer keys
are scored and published.

Full detail: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Quick start

```bash
uv venv --python 3.12 && uv sync --all-extras   # setup
uv run pytest                                   # 130 tests, no model calls
uv run scripts/score.py                         # recompute every number above
```

The last command reproduces the published results from committed artifacts alone:
no API key, no model, no raw dataset.

## Use it

Needs Claude Code, `uv` and Python 3.12. Open the repo in Claude Code: it picks up
the `review-triage` skill from `.claude/skills/` and the MCP server from
`.mcp.json` automatically, though a project-scoped server needs approving once -
run `claude`, accept it, and `claude mcp list` should then show
`review-triage ... Connected`. Then ask for a triage, for example:

> Use the review-triage skill to triage the first 20 golden-split reviews for
> Clash of Clans. Run id: my-first-run.

The skill calls `get_taxonomy`, `get_jargon_pack`, `get_reviews` and
`save_triage`, and the results land in `runs/<run id>/output.json`. Set
`TRIAGE_PACK_MODE=off` in `.mcp.json` to run without the jargon pack.

`get_reviews` only reads the review sets this repo prepares
(`data/golden/golden_pool.jsonl` and `data/interim/reviews.jsonl`), so pointing
the tool at your own CSV of reviews is not supported yet - `scripts/prepare_data.py`
expects the Kaggle dataset's columns and keeps only the two eval games.

## Limitations

- One annotator, so there is no inter-annotator agreement to report.
- Corrections were made on reviews the system itself flagged, so the corrected
  score is likely a little optimistic; the 1-in-30 control rate is the evidence
  they were mostly real.
- Two games, both extremely well known - the most likely reason the pack shows no
  effect.
- One model version; a smaller or older model might depend on the pack.

## Next steps

- Test the pack on a game the model is unlikely to know well. PUBG Mobile is held
  out and ready, and needs only a new pack file.
- Add a selective pack mode that returns only the terms occurring in the batch
  being triaged, and measure it against the full pack.
- Score the grouping step, which is produced and shown but not yet measured.
- Let `get_reviews` read from a user-supplied reviews file, and generalize
  `scripts/prepare_data.py` with column-mapping flags, so the skill can be
  pointed at someone else's reviews.

## How it works

- `.claude/skills/review-triage/SKILL.md` - fetch taxonomy, fetch pack, fetch
  reviews, triage, group, save.
- `mcp_server/server.py` - five tools over stdio on the official MCP SDK.
  `get_jargon_pack` is the only difference between the two conditions.
- `taxonomy/categories.yaml` - label space, severity rubric and boundary rules,
  shared by the skill, the labeling tool and the scorer.
- `packs/*.yaml` - one file per game; adding a game means adding one file, which
  `tests/test_add_game.py` proves.
- `scripts/` - `run_eval.py` (resumable runner), `score.py` (offline scoring),
  `labeler.py` and `relabel.py` (hand labeling).
