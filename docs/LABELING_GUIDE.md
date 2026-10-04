# Labeling guide

You are about to hand-label 180 game reviews. This guide tells you exactly what
to decide for each one, why the rule is what it is, and what to do when a review
does not fit neatly.

Budget roughly 90 minutes. You can stop and resume at any point.

---

## 1. What you are doing, and why by hand

For every review you record three things:

1. **Which issue categories apply** (zero-to-many, from a fixed list of 8)
2. **How severe it is** (high / medium / low)
3. **Whether it contains game jargon** (yes / no)

These labels become the **golden set**: the hand-made answer key that the
automated triage system is graded against.

**Why you and not a model:** the system being measured is Claude. If Claude also
wrote the answer key, the evaluation would be measuring whether Claude agrees
with itself, which tells us nothing about accuracy. So no model has seen these
reviews, suggested a label, or pre-filled anything. Your judgement is the
reference.

**Why it matters that you are consistent:** the headline result of this project
is a comparison — the same system run with the jargon pack off versus on. If your
labels drift halfway through (you get stricter about severity, say), that drift
shows up as noise in both conditions and can hide a real difference. Consistency
matters more than being "right" in some absolute sense.

### A few terms used below

| Term | What it means here |
|---|---|
| **Golden set** | The 180 reviews you are labeling. The answer key. |
| **Held out** | Kept separate and never used to build the system, so the test is fair. |
| **Dev split** | The other ~3,200 reviews. Used to build the jargon packs. You will not see these. |
| **Multi-label** | A review can carry more than one category at once. |
| **Jargon pack** | A file per game listing that game's slang, so the system can understand it. |
| **Slice** | A subset of the golden set that gets scored separately (e.g. only the jargon reviews). |
| **Severity** | How badly the player is affected, not how angry they sound. |

---

## 2. Running the tool

```bash
python scripts/labeler.py
```

It opens a page in your browser. Your work is saved after **every single review**,
so closing the tab, a crash, or a reboot loses nothing. Re-running the command
picks up where you left off.

Everything is keyboard-driven:

| Key | Action |
|---|---|
| `1`–`8` | Toggle a category on/off |
| `H` / `M` / `L` | Set severity high / medium / low |
| `J` | Toggle the "contains jargon" flag |
| `U` | Toggle "unclear" |
| `N` | Open the note box |
| `→` / `Enter` | Save and go to the next review |
| `←` | Go back and change a previous answer |

---

## 3. The three decisions

### Decision 1 — Categories

Pick every category that applies. The test is: **how many distinct problems is
this person reporting?** Two problems means two labels. One problem means one
label, and it should be the most specific category that fits.

**Ignore the star rating completely.** This is the single most important rule in
this guide, because it is the thing the project is built to measure. In this
corpus, 192 of the 652 longer reviews rated 4 or 5 stars contain an explicit
complaint. People praise a game they love and then ask for a fix in the same
breath.

> `[5 stars]` *"my game is not opening it is stuck at the loading screen"*
> → `stability_performance`, severity **high**. Five stars changes nothing.

**Praise wrapped around a complaint is still a complaint.**

> `[4 stars]` *"I hope there are more moves in hard levels especially 19k plus levels"*
> → `difficulty_balance`, severity **low**. Not `no_issue`.

### Decision 2 — Severity

Severity describes **the review as a whole**, taken from its **most severe**
issue. If someone reports a crash (high) and also dislikes the music (low), the
review is **high**.

Leave severity empty when the label is `no_issue`.

| Level | The player... |
|---|---|
| **high** | cannot play, or lost money / account / progress / owned items, or a fault keeps destroying effort they already spent |
| **medium** | can play, but the game is materially degraded, or they are repeatedly frustrated or pressured |
| **low** | is mildly annoyed, expressing taste, or requesting something that does not block play |

**Severity is not fixed per category.** Ads are usually low-to-medium, but ads
that crash the game are high. Stability is usually medium-to-high, but a small
glitch that is already fixed is low. Each category in
`taxonomy/categories.yaml` lists what escalates and de-escalates it; the short
version is in section 4 below.

**Judge impact, not tone.** An extremely angry review about the music is still
`low`. A calm, polite report of losing a 10-year account is `high`.

### Decision 3 — Does it contain jargon?

Press `J` if the review uses words someone who does not play this game would not
reliably understand: abbreviations, item names, mode names, player slang.

**Counts as jargon:** `th14`, `TH-18`, `CWL`, `war weight`, `hero hall`,
`legend league`, `gold pass`, `color bomb`, `striped candy`, `piggy bank`,
`19k plus levels`, `wooden block`.

**Does not count:** `level`, `coins`, `update`, `lag`, `ads`, `players`,
`graphics`. These are ordinary gaming words.

**Why this flag is the most valuable thing you produce:** it defines the slice of
reviews used to measure whether the jargon pack helps. The sampling code used a
keyword guess to decide which reviews to *offer* you, but that guess is crude and
is not used in any result. Your flag is the real definition. If you flag
generously, the slice gets noisy; if you flag strictly, it gets small. Aim for:
*would a smart person who has never played this game be confused by this word?*

### Also available

- **`U` — unclear.** Use it when you genuinely cannot label the text:
  unintelligible, too little context, or a language you do not read. These are
  excluded from the main scores and counted separately, so the system is never
  graded on text a human could not label either. Do not use it just because a
  review is hard — use it when it is impossible.
- **`N` — note.** A short free-text note. Use it whenever you hesitate. See
  section 7.

---

## 4. The eight categories

Each one has a plain test question, and the short version of what moves its
severity.

### 1. `stability_performance` — Stability & performance
*"Is the app failing to run properly?"*

Crashes, freezes, won't open, "connection lost", lost matches from
disconnections, lag, battery drain, storage size.

- Usually **medium**, often **high**
- **Up to high:** cannot play at all, or a fault repeatedly voids completed work
- **Down to low:** small, occasional, or already-fixed glitch

### 2. `account_progress_loss` — Account & progress loss
*"Have they lost something they persistently owned?"*

Account lost, hacked or inaccessible; progress reset; purchased or earned items
and currency disappearing; recovery that failed.

- Usually **high**
- **Stays high:** permanent, recovery already failed, account compromised
- **Down:** it was recovered, or what was lost was a streak or weekly rank rather
  than property. If they got it back and are not complaining, it is often
  `no_issue`.

### 3. `monetization` — Monetization & purchases
*"Is this about real money, or being pushed to spend it?"*

Paywalls, prices, pay-to-win, spending pressure, free routes removed, and
**paid-but-never-delivered** purchases.

- Usually **medium**
- **Up to high:** real money paid, nothing received
- **Down to low:** a general wish for cheaper prices, nothing locked away

### 4. `difficulty_balance` — Difficulty, balance & fairness
*"Does the game feel unfairly hard, badly tuned, or rigged?"*

Levels impossible, too few moves, grind, long timers, **matchmaking and ranking
systems**, perceived rigging, other players cheating, stale repetitive content.

- Usually **medium**
- **Up to high:** progression completely blocked for days, no way forward
- **Down to low:** a tuning suggestion with nothing actually blocked

> Note: matchmaking and league complaints live here rather than in their own
> category. That was a deliberate trade — with 180 reviews, a separate
> matchmaking category would have had too few examples to score meaningfully.

### 5. `ads` — Advertising
*"Is this about adverts?"*

Too many, badly placed, unskippable, failing or crashing, **rewards promised for
watching an ad that never arrive**, misleading ad content.

- Usually **low to medium**
- **Up to high:** ads crash the game, loop, or cannot be dismissed
- **Down to low:** only about ad content, length or repetition, play not interrupted

### 6. `content_ux` — Content, features & UX
*"Are they asking for something, or complaining about the interface?"*

Feature requests, "bring back X", removed or changed content, popup clutter,
confusing navigation, missing settings, language requests, chat and social
features, music and art changes.

- Usually **low**
- **Up:** a missing option blocks something with no workaround, or the game
  interferes with the phone outside itself
- **Down to low:** cosmetic or a matter of taste

### 7. `other_issue` — Other issue
*"Is this a real problem that genuinely fits nothing above?"*

**This is a fallback, not an extra tag.** Never combine it with another category.
In practice it catches two things: customer support being unresponsive (when it
is not about account recovery), and vague negativity with no identifiable
problem.

- **Medium** when a process has failed the player and left them stuck
- **Low** when it is only sentiment, e.g. *"worst game"* with no detail

### 8. `no_issue` — No actionable issue
*"Is there genuinely nothing to act on?"*

Pure praise, neutral chatter, nostalgia, off-topic text.

- **Cannot be combined with anything else.** Severity stays empty.
- This is the right answer for most 5-star reviews — but check for a complaint
  buried at the end first.

---

## 5. The four hard cases

These overlaps are decided once, here, so your labels stay consistent.

### A technical fault destroyed something — one label or two?

**Rule:** `account_progress_loss` is about **persistent property** — the account,
saved progress, owned inventory. A **single voided match or session** is
`stability_performance` alone, because that loss is just the fault's immediate
effect.

> *"my attack is gone and counted as a loss"*
> → `stability_performance` only. One session.

> *"Everytime I get kicked out, I lose lives and any special items I tried to use"*
> → `stability_performance` **and** `account_progress_loss`. A fault **plus**
> repeated loss of owned inventory: two problems.

### Paid, but never received it

**Rule:** `monetization`, severity **high**. It is a failed transaction, not lost
property — they never had the goods. Real money is gone, so it is high.

> *"i paid for 10 gold bars but i didn't receive any"* → `monetization`, high.

Contrast with inventory they already owned vanishing:

> *"I suddenly lost my boosters, pin collection, gold!!"* → `account_progress_loss`.

### Watched an ad, got no reward

**Rule:** `ads` only. The ad system failed. `monetization` needs **real money** or
a paywall — watching an ad costs attention, not money.

> *"after watching ad there is no prize given"* → `ads`.

### Too hard unless you pay

**Rule:** **both** `difficulty_balance` and `monetization`, when the review claims
the difficulty exists *in order to* extract money. That is two assertions: the
tuning is unfair, and it is unfair by design to sell something.

> *"packed with levels that are impossible to beat without spending money ...
> specifically designed so that you would spend"*
> → `difficulty_balance` **and** `monetization`.

> *"at a certain level, it's impossible to pass and not fun anymore"*
> → `difficulty_balance` only. Hard, with no spending claim.

> *"level 600+ is just impossible to beat without golds and watching ads"*
> → `difficulty_balance`, `monetization` **and** `ads`. All three are asserted.

---

## 6. Keyword traps

A word appearing does not put a review in that category. Read what actually
happened.

> `[5]` *"OMG I RECOVERED MY 7 YEAR OLD ACCOUNT INSTANTLY THANK YOU SUPERCELL"*
> → `no_issue`. Account recovery is mentioned, but nothing went wrong.

> `[3]` *"relaxing. lost my winning streak at 92"*
> → `no_issue`. "Lost" appears, but losing a streak by playing badly is ordinary
> gameplay, not a fault and not a loss of property.

> `[5]` *"you can just watch a ad for another life"*
> → `no_issue`. Ads mentioned approvingly.

---

## 7. Notes and the second pass

Press `N` and write a few words whenever you hesitate — *"severity medium or
high?"*, *"is this jargon?"*, *"monetization too?"*. Do not stall on a hard
review: make your best call, note it, move on.

When you reach the end, the tool offers a **review-notes pass**: it lists every
review you noted, together, so you can settle them as a group.

**Why a second pass matters:** deciding five similar hard cases side by side is
far more consistent than deciding each one in isolation twenty minutes apart.
Most annotation inconsistency comes from exactly that drift. Notes are never
scored — they exist for you and for the write-up.

---

## 8. Practical tips

- **Go with your first instinct** on easy reviews. Most are easy.
- **Do not reverse-engineer the star rating.** If your label disagrees with the
  stars, that is often the most valuable label in the set.
- **Do not try to balance the categories.** If 60% come out `no_issue`, that is a
  finding, not a mistake.
- **Take a break around review 90.** Fatigue shows up as severity drift.
- **If you change your mind about a rule mid-way**, write it in a note and tell
  me at the end — we can re-check the affected reviews rather than silently
  carrying two standards.

---

## 9. What happens next

Your labels are saved to `data/golden/golden_set.jsonl` and committed, because
they are the most valuable artifact in this repo. Then:

1. The same triage skill is run over these reviews twice — jargon pack **off**,
   then **on** — three times each, to show run-to-run variance.
2. Every metric is computed offline from the saved outputs, so anyone can
   recompute the results without calling a model.
3. Scores are broken out by slice: random vs enriched, and
   **jargon vs non-jargon using your `J` flag**. That breakdown is the result
   the README leads with.
