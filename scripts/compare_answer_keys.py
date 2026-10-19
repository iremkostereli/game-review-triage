"""Print the two answer keys side by side: original labels and corrected labels.

    uv run scripts/compare_answer_keys.py

Reads results/metrics.json and results/metrics_corrected.json, both produced by
scripts/score.py. No model is called.
"""

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"
if not (R / "metrics.json").exists():
    sys.exit("run scripts/score.py first")
orig = json.loads((R / "metrics.json").read_text(encoding="utf-8"))
if not (R / "metrics_corrected.json").exists():
    sys.exit("no corrected metrics; add data/golden/corrections.jsonl and re-score")
corr = json.loads((R / "metrics_corrected.json").read_text(encoding="utf-8"))

METRICS = [("category_micro.f1","Kategori micro-F1"),
           ("category_macro_f1","Kategori macro-F1"),
           ("exact_set_match","Tam etiket seti"),
           ("issue_detection.f1","Issue / no_issue F1"),
           ("severity.accuracy","Severity dogrulugu")]

def mean(rep, mode, slc, metric):
    return rep["variance"][mode][slc][metric]["mean"]

print("=== 1. BORU HATTI SKORLARI (tum 178 yorum) ===")
print(f"{'metrik':<22}{'ORIJINAL OFF':>14}{'ORIJINAL ON':>13}{'DUZELT. OFF':>14}{'DUZELT. ON':>13}")
for m, label in METRICS:
    print(f"{label:<22}{mean(orig,'off','all',m):>14.3f}{mean(orig,'on','all',m):>13.3f}"
          f"{mean(corr,'off','all',m):>14.3f}{mean(corr,'on','all',m):>13.3f}")

if not orig.get("comparison"):
    print()
    print("No confidence intervals in results: scores were computed with --no-bootstrap.")
    sys.exit(0)

print()
print("=== 5. PAKET ON - OFF FARKI, IKI ANAHTAR ALTINDA (micro-F1) ===")
print(f"{'dilim':<22}{'n':>5}{'ORIJINAL fark':>30}{'DUZELTILMIS fark':>30}")
for slc, label in [("all","Tumu"),("jargon","Jargonlu"),("no_jargon","Jargonsuz"),
                   ("slice_random","Random dilim"),("slice_enriched","Enriched dilim")]:
    a = orig["comparison"][slc]["category_micro.f1"]
    b = corr["comparison"][slc]["category_micro.f1"]
    fa = f"{a['delta']:+.3f} [{a['ci_low']:+.3f},{a['ci_high']:+.3f}]" + (" *" if a["significant"] else "")
    fb = f"{b['delta']:+.3f} [{b['ci_low']:+.3f},{b['ci_high']:+.3f}]" + (" *" if b["significant"] else "")
    print(f"{label:<22}{a['n']:>5}{fa:>30}{fb:>30}")

print()
print("=== jargon bayragi uyumu farki (iki anahtar) ===")
for slc, label in [("all","Tumu"),("jargon","Jargonlu"),("no_jargon","Jargonsuz")]:
    a = orig["comparison"][slc]["jargon_flag_agreement"]
    b = corr["comparison"][slc]["jargon_flag_agreement"]
    fa = f"{a['delta']:+.3f} [{a['ci_low']:+.3f},{a['ci_high']:+.3f}]" + (" *" if a["significant"] else "")
    fb = f"{b['delta']:+.3f} [{b['ci_low']:+.3f},{b['ci_high']:+.3f}]" + (" *" if b["significant"] else "")
    print(f"{label:<22}{a['n']:>5}{fa:>30}{fb:>30}")
print()
print("not: jargon bayragi etiketleri duzeltmelerde degismedi, o yuzden iki anahtarda ayni olmasi beklenir")
