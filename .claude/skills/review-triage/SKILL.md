---
name: review-triage
description: >-
  Triage mobile game app reviews into actionable LiveOps issues: assign issue
  categories and a severity to each review, flag game-specific jargon, and group
  related reviews into issues with quoted evidence. Use when asked to triage,
  categorise or analyse game reviews, or when running the review-triage eval.
---

# Review triage

You turn raw app-store reviews into something a LiveOps team can act on.

All data, the label space and the game vocabulary come from the `review-triage`
MCP server. Do not invent categories, and do not rely on memory for what a game's
slang means.

## Procedure

Follow these steps in order. Do not skip a step even if you think you already
know the answer, because the run trace is checked for these calls.

1. **`get_taxonomy`** — fetch the categories, their boundary rules and the
   severity rubric. The category ids you output must come from here verbatim.

2. **`get_jargon_pack`** with the game name — fetch that game's vocabulary.

   This may come back with zero terms. That is a legitimate, expected state: the
   pack may be switched off for this run, or the game may not have one. **Work
   with exactly what you are given.** If it is empty, interpret the reviews using
   ordinary language understanding and do not substitute remembered knowledge
   about the game. If it has terms, use them to read the reviews correctly.

3. **`get_reviews`** — fetch the reviews to triage, paging with `limit` and
   `offset` until you have them all. Default split is `golden`.

4. **Triage every review** as described below.

5. **Group** the triaged reviews into issues with evidence.

6. **`save_triage`** once per game with every review you triaged and your issue
   groups. Use the `run_id` given to you in the task.

## Triaging one review

For each review produce:

- `reviewId` — exactly as given
- `categories` — a list of category ids from the taxonomy
- `severity` — `high`, `medium` or `low`; `null` when the category is `no_issue`
- `has_jargon` — `true` if the review uses vocabulary specific to this game that
  a non-player would not reliably understand
- `jargon_terms` — the specific phrases you judged to be jargon (empty list if
  none)
- `rationale` — one short sentence on why these labels

### Rules that decide most cases

- **Ignore the star rating.** Players often report real problems while giving 4
  or 5 stars. Label the text, not the score.
- **Count the distinct problems.** Two problems means two categories. One problem
  means one category, and it should be the most specific one that fits.
- **`no_issue` is exclusive** and takes no severity. Use it for praise and
  neutral chatter only.
- **`other_issue` is a fallback**, never an extra tag. Only use it when nothing
  else fits.
- **Severity is about impact, not tone.** A furious review about background music
  is still `low`. A calm report of a lost account is `high`.
- **Severity is not fixed per category.** Each category's `severity_guidance`
  states its typical level and what escalates or de-escalates it. Apply it.
- The taxonomy's `boundaries` section decides the overlapping cases (a crash that
  destroys progress, a purchase that never arrived, an ad reward that was not
  granted, difficulty that pushes spending). Follow it rather than improvising.

### On `has_jargon` and `jargon_terms`

Judge the text itself. Abbreviations, item names, mode names and player slang
count. Ordinary gaming words — level, coins, update, lag, ads, graphics — do not.

Set these fields from what the review says, not from whether the pack happened to
contain the term. A review can contain jargon that is missing from the pack, and
a pack term can appear in a review in an ordinary, non-jargon sense.

## Grouping into issues

After triaging, group reviews that describe the same underlying problem. For each
group give:

- `title` — a short, specific problem statement a LiveOps team could act on
- `category` — the primary category id
- `severity` — the group's severity
- `review_ids` — the member reviews
- `evidence` — two or three short verbatim quotes from those reviews

Prefer a few well-evidenced groups over many thin ones. Leave a review ungrouped
rather than forcing it somewhere.

## Output discipline

- Use category ids and severity values exactly as the taxonomy spells them.
- Every review you were given must appear exactly once in `results`.
- Quote evidence verbatim; never paraphrase inside `evidence`.
- If a review is unintelligible, still label it: your best judgement plus a
  rationale saying it is unclear.
