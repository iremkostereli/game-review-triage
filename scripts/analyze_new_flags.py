"""Which reviews became newly over-flagged with the pack on, and why."""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage import packs, paths, scoring
from triage.jsonl_io import read_json, read_jsonl

gold = scoring.load_gold()
text = {r["reviewId"]: r["content"] for r in read_jsonl(paths.GOLDEN_SET)}

vocab = {}
for game in packs.list_games():
    vocab[game] = {f.lower(): t.term for t in packs.load_pack(game).terms
                   for f in (t.term, *t.aliases)}

flag = defaultdict(lambda: defaultdict(int)); cite = defaultdict(lambda: defaultdict(Counter))
reps = defaultdict(set)
for m in sorted(paths.RUNS_DIR.glob("*/meta.json")):
    d = read_json(m)
    if d.get("status") != "ok": continue
    o = m.parent / "output.json"
    if not o.exists(): continue
    reps[d["pack_mode"]].add(d["repeat"])
    for r in read_json(o).get("results", []):
        rid = r.get("reviewId")
        if not rid: continue
        if r.get("has_jargon"): flag[d["pack_mode"]][rid] += 1
        for p in r.get("jargon_terms") or []:
            cite[d["pack_mode"]][rid][p.strip().lower()] += 1

def flagged(mode, rid): return flag[mode].get(rid, 0) * 2 > len(reps[mode])

# Ordinary words a non-player would understand, per the labeling guide's rule.
GENERIC = {"Moves", "Extra Moves", "Lives", "Gold Bars", "Gold", "Troops", "Booster",
           "Hard Level", "Race", "Team", "Episode", "Clan War", "Elixir", "Gems",
           "Village", "Hero", "Spell", "Trophies", "Loot"}

new = [rid for rid in gold
       if not gold[rid].has_jargon and flagged("on", rid) and not flagged("off", rid)]
print(f"\nnewly over-flagged with the pack ON: {len(new)} reviews\n")
only_generic = 0
for rid in new:
    g = gold[rid]
    phrases = list(cite["on"][rid])
    terms = []
    for p in phrases:
        hit = next((t for f, t in vocab[g.game].items() if len(f) >= 4 and f in p), None)
        terms.append((p, hit))
    mapped = [t for _, t in terms if t]
    if mapped and all(t in GENERIC for t in mapped) and len(mapped) == len(terms):
        only_generic += 1
        mark = "ORDINARY-WORD PACK TERMS ONLY"
    else:
        mark = ""
    print(f"[{g.game[:5]}] {g.score}* {rid[:8]} {mark}")
    print(f"   text: {text[rid][:120]}")
    print(f"   cited: {[(p, t) for p, t in terms]}")
print(f"\n{only_generic}/{len(new)} of the new over-flags cite only pack terms that are "
      f"ordinary words a non-player would understand")
