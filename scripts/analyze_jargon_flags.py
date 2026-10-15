"""Why does the jargon-flag agreement move when the pack is on?

For every review where a condition flagged jargon but the annotator did not, list
the phrases the model cited and say whether each one is a pack term. The question
being answered: is the drop driven by pack terms that the labeling guide would not
count as jargon (ordinary words like moves, lives, gold, troops)?
"""

import sys
from collections import Counter, defaultdict

sys.path.insert(0, r"C:\Users\user\Desktop\game_review")

from triage import packs, paths, scoring
from triage.jsonl_io import read_json

gold = scoring.load_gold()

# Pack vocabulary per game: main terms plus aliases, lowercased -> main term.
pack_vocab: dict[str, dict[str, str]] = {}
for game in packs.list_games():
    pack = packs.load_pack(game)
    vocab: dict[str, str] = {}
    for term in pack.terms:
        for form in (term.term, *term.aliases):
            vocab[form.lower()] = term.term
    pack_vocab[game] = vocab


def pack_term_for(game: str, phrase: str) -> str | None:
    """The pack term a cited phrase corresponds to, if any."""
    vocab = pack_vocab.get(game, {})
    phrase = phrase.strip().lower()
    if phrase in vocab:
        return vocab[phrase]
    # A cited phrase often contains a pack term rather than equalling it,
    # e.g. "19k plus levels" or "th13 base".
    for form, term in vocab.items():
        if len(form) >= 4 and form in phrase:
            return term
    return None


flagged: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
cited: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
seen: dict[str, set[str]] = defaultdict(set)
repeats: dict[str, set[int]] = defaultdict(set)

for meta_path in sorted(paths.RUNS_DIR.glob("*/meta.json")):
    meta = read_json(meta_path)
    if meta.get("status") != "ok":
        continue
    output_path = meta_path.parent / "output.json"
    if not output_path.exists():
        continue
    mode = meta["pack_mode"]
    repeats[mode].add(int(meta["repeat"]))
    for result in read_json(output_path).get("results", []):
        review_id = result.get("reviewId")
        if not review_id:
            continue
        seen[mode].add(review_id)
        if result.get("has_jargon"):
            flagged[mode][review_id] += 1
        for phrase in result.get("jargon_terms") or []:
            cited[mode][review_id][phrase.strip().lower()] += 1

print("repeats per condition:", {m: sorted(r) for m, r in repeats.items()})
print("reviews seen per condition:", {m: len(s) for m, s in seen.items()})
print()

for mode in ("off", "on"):
    scored = [rid for rid in gold if rid in seen[mode]]
    gold_yes = [rid for rid in scored if gold[rid].has_jargon]
    # A review counts as flagged if a majority of that condition's repeats flagged it.
    n_repeats = max(1, len(repeats[mode]))
    def is_flagged(rid: str) -> bool:
        return flagged[mode].get(rid, 0) * 2 > n_repeats

    false_pos = [rid for rid in scored if is_flagged(rid) and not gold[rid].has_jargon]
    false_neg = [rid for rid in gold_yes if not is_flagged(rid)]

    print(f"=== pack {mode.upper()} ({len(scored)} reviews scored) ===")
    print(f"  annotator flagged jargon: {len(gold_yes)}")
    print(f"  model flagged but annotator did not: {len(false_pos)}")
    print(f"  annotator flagged but model did not: {len(false_neg)}")

    phrases = Counter()
    for rid in false_pos:
        for phrase in cited[mode][rid]:
            phrases[(gold[rid].game, phrase)] += 1

    in_pack = 0
    print(f"  phrases cited on those over-flagged reviews (top 30 of {len(phrases)}):")
    for (game, phrase), count in phrases.most_common(30):
        term = pack_term_for(game, phrase)
        if term:
            in_pack += count
        label = f"pack term '{term}'" if term else "not in the pack"
        print(f"    {count:>3}x [{game[:5]}] {phrase!r:<34} {label}")

    total = sum(phrases.values())
    matched = sum(c for (g, p), c in phrases.items() if pack_term_for(g, p))
    if total:
        print(f"  of {total} cited phrases, {matched} are pack terms "
              f"({100 * matched / total:.0f}%)")
    print()
