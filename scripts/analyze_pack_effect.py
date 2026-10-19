"""Where did the pack change the answer, and does the reasoning mention jargon?

Finds jargon-flagged reviews whose category labels differ between the conditions,
and prints the review text next to each condition's own stated rationale. The
question being answered: when the pack is off, are the mistakes actually caused
by misreading game vocabulary, or by something else entirely?
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import packs, paths, scoring
from triage.jsonl_io import read_json, read_jsonl

gold = scoring.load_gold()
text = {row["reviewId"]: row["content"] for row in read_jsonl(paths.GOLDEN_SET)}

pack_vocab: dict[str, dict[str, str]] = {}
for game in packs.list_games():
    pack = packs.load_pack(game)
    pack_vocab[game] = {
        form.lower(): term.term
        for term in pack.terms
        for form in (term.term, *term.aliases)
    }


def pack_terms_in(game: str, content: str) -> list[str]:
    lowered = content.lower()
    found = []
    for form, term in pack_vocab.get(game, {}).items():
        if len(form) >= 4 and form in lowered and term not in found:
            found.append(term)
    return found


# reviewId -> mode -> list of (categories, severity, rationale) across repeats
preds: dict[str, dict[str, list[tuple[frozenset, str | None, str]]]] = defaultdict(
    lambda: defaultdict(list)
)
for meta_path in sorted(paths.RUNS_DIR.glob("*/meta.json")):
    meta = read_json(meta_path)
    if meta.get("status") != "ok":
        continue
    output_path = meta_path.parent / "output.json"
    if not output_path.exists():
        continue
    for result in read_json(output_path).get("results", []):
        review_id = result.get("reviewId")
        if review_id:
            preds[review_id][meta["pack_mode"]].append(
                (
                    frozenset(result.get("categories") or []),
                    result.get("severity"),
                    (result.get("rationale") or "").strip(),
                )
            )


def majority(entries):
    """The label set this condition produced most often."""
    counts = defaultdict(int)
    for categories, _, _ in entries:
        counts[categories] += 1
    return max(counts.items(), key=lambda kv: kv[1])[0] if counts else None


interesting = []
for review_id, by_mode in preds.items():
    if review_id not in gold or not gold[review_id].has_jargon:
        continue
    if "off" not in by_mode or "on" not in by_mode:
        continue
    off_set, on_set = majority(by_mode["off"]), majority(by_mode["on"])
    truth = gold[review_id].categories
    off_right, on_right = off_set == truth, on_set == truth
    if off_right != on_right:
        interesting.append((review_id, off_set, on_set, off_right, on_right))

on_better = [x for x in interesting if x[4]]
off_better = [x for x in interesting if x[3]]
print(f"jargon-flagged reviews where exactly one condition matched the answer key:")
print(f"  pack ON right, OFF wrong: {len(on_better)}")
print(f"  pack OFF right, ON wrong: {len(off_better)}")
print()

for title, group in (("PACK ON FIXED IT", on_better), ("PACK ON BROKE IT", off_better)):
    print(f"########## {title} ({len(group)}) ##########")
    for review_id, off_set, on_set, _, _ in group[:12]:
        g = gold[review_id]
        print(f"\n[{g.game}] [{g.score} stars] {review_id[:8]}")
        print(f"  review: {text.get(review_id, '')[:260]}")
        print(f"  pack terms present in the text: {pack_terms_in(g.game, text.get(review_id, '')) or 'none'}")
        print(f"  gold:    {sorted(g.categories)}  severity={g.severity}")
        print(f"  OFF:     {sorted(off_set)}")
        for _, _, rationale in preds[review_id]['off'][:2]:
            print(f"     why: {rationale[:170]}")
        print(f"  ON:      {sorted(on_set)}")
        for _, _, rationale in preds[review_id]['on'][:2]:
            print(f"     why: {rationale[:170]}")
    print()
