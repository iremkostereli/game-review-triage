# Methodology

Detail behind the headline numbers in the [README](../README.md). Every figure
comes from `uv run scripts/score.py`, which reads the committed answer key and run
outputs and calls no model.

## Corpus and split

10,000 Google Play reviews for four games, 31 January to 17 February 2026. Clash
of Clans and Candy Crush Saga are used for the eval; PUBG Mobile and Subway
Surfers are held out entirely.

Reviews here are short: the median is 3 to 5 words, and only 886 of the two eval
games' 5,000 reviews reach 12 words, so a uniform sample would have been mostly
one-word praise with no jargon in it. Sampling is stratified into two slices,
scored separately:

- **random** (58 reviews) - uniform over reviews of 12+ words, an honest base
  rate, honest about being conditional on length;
- **enriched** (120 reviews) - over-samples jargon-bearing reviews and high-star
  reviews that carry a complaint.

Selection is driven by `sha256(reviewId)` rather than a random number generator,
so the split reproduces anywhere with no seed and reruns are byte-identical, and
duplicate review text is dropped first so the same string cannot land on both
sides of the held-out boundary. The golden set is 180 reviews (Clash 100, Candy
80), fingerprint `b38d5821c3f1`. Two were marked unlabelable and are withheld
from scoring, leaving 178 (Clash 99, Candy 79), of which 71 are flagged as
containing jargon.

## Categories

From `taxonomy/categories.yaml`, the single source of truth shared by the skill,
the labeling tool and the scorer.

| Category | What it covers | Typical severity |
|---|---|---|
| `stability_performance` | Crashes, freezes, failures to launch, disconnections, lost matches, lag, battery, storage | medium, often high |
| `account_progress_loss` | Loss of, or lost access to, persistent property: the account, saved progress, purchased or earned items | high |
| `monetization` | How the game asks for real money, or a real-money transaction gone wrong: paywalls, pricing, pay-to-win, spending pressure, paid-but-not-delivered | medium |
| `difficulty_balance` | Unfairly hard, badly tuned or rigged: difficulty, economies, grind and timers, matchmaking and ranking, perceived rigging | medium |
| `ads` | Ad volume and placement, ads that fail or crash, promised ad rewards that never arrive, misleading creative | low to medium |
| `content_ux` | Feature and content requests, removed or changed content, interface friction: clutter, popups, navigation, settings, localisation | low |
| `other_issue` | A real issue none of the six above covers; mostly support responsiveness and vague negativity | medium when a process failed the player, else low |
| `no_issue` | Praise, neutral chatter, nostalgia, off-topic text. **Exclusive** | none; always empty |

Severity is `high` (cannot play, or lost money, account, progress or owned items,
or a defect that repeatedly destroys effort), `medium` (playable but materially
degraded, or repeatedly frustrated or pressured) or `low` (minor annoyance, taste,
or a request that does not block play), and empty for `no_issue`.

## Labeling rules

One annotator labeled every review by hand. No model pre-labeled anything or saw
the reviews before the eval runs: the system being measured is also Claude, so
model involvement in the answer key would make the comparison meaningless.

- **Ignore the star rating**; 192 of the 652 reviews with 4+ stars and 10+ words
  carry an explicit complaint, and praise around a complaint is still a complaint.
- **Multi-label by distinct problems**: two problems, two labels; one problem, one
  label and the most specific category covering it.
- **Severity is review-level and about impact, not tone**, from the most severe
  issue. A furious review about music is still `low`.
- **`no_issue` is exclusive** and takes no severity; **`other_issue` is a
  fallback**, never an extra tag. Vague negativity is `other_issue` at `low`.
- **`monetization` needs real money or spending pressure**; stingy in-game rewards
  are `difficulty_balance`.
- **Hard cases, decided once.** A fault destroying persistent property is both
`stability_performance` and `account_progress_loss`, but a single voided session
is stability alone; paid-and-never-delivered is `monetization` at high, while
owned inventory vanishing is `account_progress_loss`; an ad reward not granted
is `ads` only; difficulty asserted to exist in order to extract money is both
`difficulty_balance` and `monetization`. A keyword is never a category on its
own - a review can mention losing something, paying or ads and not belong in
that category.
- **`has_jargon`** is true when the review uses vocabulary a non-player would not
  reliably understand - `th14`, `CWL`, `color bomb`, `19k plus levels` - but not
  ordinary gaming words like level, coins or lag. **That hand-set flag, not the
  sampling heuristic in `triage/sampling_terms.py`, defines the jargon slice in
  every result.**

A blind second pass with controls corrected 32 labels, each recorded with a reason
in `data/golden/corrections.jsonl`. The original `golden_set.jsonl` is never
modified: corrections are applied at scoring time, and both answer keys are scored
and published.

## The pack experiment

The condition travels only through `get_jargon_pack`: same skill, same model, and
a prompt built once per batch and reused byte-for-byte across conditions, which
the runner asserts. Every run's trace is checked to confirm which condition it was
actually in, and a run whose trace disagrees is discarded rather than scored.

Category micro-F1, ON minus OFF, 95% paired bootstrap intervals over reviews
(2,000 resamples, fixed seed). Reviews are the sampling unit and the pairing is
kept, since the headline is a difference measured on the same reviews.

| Slice | n | Corrected key | Original key |
|---|---|---|---|
| All | 178 | +0.000 [-0.014, +0.015] | +0.000 [-0.014, +0.015] |
| Jargon reviews | 71 | -0.006 [-0.033, +0.019] | -0.006 [-0.032, +0.019] |
| Non-jargon reviews | 107 | +0.004 [-0.011, +0.021] | +0.004 [-0.011, +0.022] |

No interval excludes zero, and the overall one rules out any effect larger than
about 1.5 points: a measured null rather than an underpowered one.

The one measurable effect is a loss. Agreement with the hand-set jargon flag
falls from 0.875 to 0.824 overall, `-0.051 [-0.090, -0.015]`, entirely on
reviews the annotator did *not* consider jargon-bearing, `0.869` to `0.776`,
`-0.093 [-0.153, -0.037]`; on the ones they did flag it is marginally better,
`+0.014 [-0.014, +0.042]`. Per `uv run scripts/analyze_new_flags.py`, 11 of the
13 reviews newly over-flagged with the pack on cite only ordinary pack terms
such as `extra moves`, `lives` and `gold`, and all 11 are Candy Crush, whose
pack is where those common words live. Being listed in a pack is itself a signal
that a word is special, and for ordinary words that signal is wrong.

There is also nothing for the pack to fix. `uv run
scripts/analyze_pack_effect.py` prints each condition's own reasoning on the
jargon reviews where they disagreed: only 4 of 71 changed their correctness, and
in the three the pack fixed, the pack-off reasoning already shows the vocabulary
understood - "Wants an opt-out of being attacked like the builder base has",
"Legend League title removed from profile". The errors were category choices,
not misreadings. The one the pack broke runs the other way: the `Booster` hint
says levels impossible without boosters are monetization as well as difficulty,
and the model added `monetization` where the annotator had not.

## Pack sourcing rules

A term enters a pack only if it appears in the **dev split**, or the
**publisher's own documentation** names it as a game element - never by reading
the golden set. That rule is what stops a pack being quietly fitted to the test
data, and it caught two real mistakes: `striped candy` and `glass candy` had been
added from memory, and both occur only in held-out golden reviews.

Meanings are written in our own words from the publisher's help centre, never
copied, each citing its page. A term the publisher does not define is marked
`source: inferred_from_reviews`, says only what the cited dev reviews show, and
lists those ids as evidence; no URL is ever invented, and local copies of the
pages stay out of the repo. Aliases must be attested too: in a dev review, a
plain spelling variant, or declared as appearing on the cited page.
`tests/test_leakage.py` enforces all of this, including that no pack evidence id
belongs to the golden set. The packs are deliberately whole rather than trimmed,
since cutting them to the terms that happen to appear in the test data would be
exactly the bias the sourcing rule exists to prevent; a selective mode is a next
step so the trimmed version can be measured rather than assumed better.

## Running the eval, and getting the data

```bash
uv run scripts/run_eval.py --limit 20 --repeats 1   # cheap smoke run
uv run scripts/run_eval.py                          # full: 2 conditions x 3 repeats
```

Each batch is a headless `claude -p` invocation that loads the real skill and
talks to the real MCP server; completed batches are skipped on re-run. Two details
matter. A run is judged by its **trace and saved output, not its exit code**,
because a run can finish all of its work and still return non-zero when a session
usage limit lands after the final tool call. And the condition must travel in a
**generated MCP config, not an exported environment variable**, since an `env`
block in an MCP config overrides the shell - a run labelled ON that had actually
run OFF was caught this way.

The raw dataset is not committed. Download
[game-reviews](https://www.kaggle.com/datasets/araraltawil/game-reviews) from
Kaggle, put `game_reviews.csv` in `data/raw/`, then run `uv run
scripts/prepare_data.py`. The golden set, run outputs and traces are committed,
so `uv run pytest` and `uv run scripts/score.py` work without it.
