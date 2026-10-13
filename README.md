# Game review triage

A Claude Code skill plus an MCP server that triages mobile game app reviews into
actionable LiveOps issues: issue categories, a severity, and grouped issues with
quoted evidence. Its distinguishing feature is pluggable per-game **jargon
packs** — one YAML file per game that teaches the skill that game's vocabulary.

The experiment this repo exists to run: the same skill, over the same held-out
reviews, with the jargon pack **off** and then **on**, scored against a
hand-labeled golden set.

> **Work in progress.** Results, setup instructions and the full write-up land in
> the final phase. What follows is the part that is already settled.

## Setup

```bash
uv venv --python 3.12
uv sync --all-extras
```

Everything then runs through `uv run ...`, which keeps this project's
dependencies out of your global Python environment.

## How jargon packs are built

A pack is a glossary with a triage opinion: every term carries a `meaning` and a
`triage_hint` saying what a mention of it usually signals in taxonomy terms.

**Term selection rule.** A term goes into a pack if either

- **(a)** it appears in the **dev split** of the review corpus, or
- **(b)** the publisher's own documentation names it as a game element — for
  Candy Crush Saga, anything King's help centre lists as a Booster, a Special
  Candy or a Blocker; for Clash of Clans, anything Supercell's support pages name.

**Terms are never chosen by reading the golden set.** That is the point of rule
(b): the publisher's catalogue decides what belongs in the pack, so the pack
cannot be quietly fitted to the test set. During development this rule caught two
real mistakes — `striped candy` and `glass candy` had been added from memory, and
both turn out to occur *only* in held-out golden reviews.

**Sourcing.** Meanings are written in our own words. A term is `source:
official` only when a publisher page actually defines it, and then it cites that
page's URL. Otherwise it is `source: inferred_from_reviews`, its meaning says
only what the cited dev reviews show, and it lists those review ids as evidence.
No URL is ever invented. Local copies of the help-centre pages live in
`sources/`, which is gitignored because the pages are copyrighted.

**Aliases.** Player slang and abbreviations map onto the main term. Every alias
must be attested: present in a dev review, a plain spelling variant of the term,
or explicitly declared in `source_aliases` as appearing on the cited official
page. `tests/test_leakage.py` enforces all of this, including that no pack
evidence id belongs to the golden set.

**Triage hints state possible causes, never verdicts.** Several official pages
explain that a complaint has a designed cause — trophies reset at season end,
resources do not disappear on their own. Those explanations are recorded as
context only. Category and severity always follow what the review itself claims;
a hint must not be used to dismiss a complaint.

### Adding a game

Write one YAML file in `packs/`. Nothing else: no code changes, no skill changes.
Games are discovered by scanning the directory, and `tests/test_add_game.py`
proves it by dropping a pack into a temporary directory and checking the new game
appears. Start from `packs/_TEMPLATE.yaml`.

### Pack size

The packs are deliberately whole rather than trimmed:

| Game | Terms | Official | Inferred | Approx. tokens |
|---|---|---|---|---|
| Candy Crush Saga | 47 | 37 | 10 | ~5,400 |
| Clash of Clans | 50 | 45 | 5 | ~6,300 |

That means a pack includes documented elements that never appear in any review in
this corpus. Keeping them is a deliberate trade: selecting only the terms that
show up would mean choosing terms by looking at the data the system is scored on,
which is exactly the bias the selection rule above is designed to remove. The
cost is a larger prompt, and possibly some distraction for the model — which is
itself something the eval can measure.

## Known limitations

- Candy Crush's official help centre documents boosters, candies, blockers, lives
  and controls well, but not its live-service features. Terms like *legendary
  level*, *streak*, *race* and *sweet cinema* are therefore
  `inferred_from_reviews`, defined only from what players say about them.
- The Supercell and King help-centre pages are JavaScript-rendered, so their text
  was read from local copies rather than fetched directly. Each term cites its
  page so the meaning can be checked against the source.

## Next steps

- **A selective pack mode.** `get_jargon_pack` currently returns the whole pack.
  Add a mode that returns only the terms whose name or alias actually occurs in
  the batch of reviews being triaged, and measure it against the full pack: it
  should cut prompt size sharply, and the comparison would show whether the
  unused terms were helping, harmless or actively distracting.
- Score the grouping step, which is currently produced and shown but not measured.
- Jargon span labeling, so pack coverage can be measured per phrase.
- The held-out games: PUBG Mobile first, then Subway Surfers.
- Fan wiki sources, which are excluded for now.
- A second annotator, so inter-annotator agreement can be reported.

## Hardest part

<!-- To be written by the repo author. -->
