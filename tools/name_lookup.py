#!/usr/bin/env python3
"""
name_lookup — which Thai rendering to use for a Chinese name/term (read-only).

    python -I tools/name_lookup.py 长鸣珠 安西 狂澜 千莳余响

For each term it prints the candidates and how often each one already appears in
finished translations of texts that contain the term, then a pick:
  1. glossary/series_names.tsv   (fixed series/place/item names — always wins)
  2. glossary/glossary.tsv        (approved terms — must be used)
  3. otherwise the rendering used MOST OFTEN in finished translations
     (the DB row of the exact term can be a minority variant — do not trust it alone)
If nothing is known it prints the Mandarin transliteration from translit.py.
"""
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def load(path, key="zh"):
    with open(path, encoding="utf-8") as f:
        return {r[key]: r for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    terms = sys.argv[1:]
    if not terms:
        print(__doc__)
        return 1
    series = load(ROOT / "glossary" / "series_names.tsv")
    gloss = load(ROOT / "glossary" / "glossary.tsv")
    con = sqlite3.connect(ROOT / "work" / "wwm.db")
    try:
        import translit
        tl = translit.translit if hasattr(translit, "translit") else None
    except Exception:
        tl = None
    for t in terms:
        cands = {}
        if t in series:
            cands[series[t]["th"]] = "series_names"
            for v in filter(None, series[t]["variants"].split("|")):
                cands.setdefault(v, "variant (avoid)")
        if t in gloss and gloss[t]["th"]:
            cands.setdefault(gloss[t]["th"], f"glossary {gloss[t]['status']}")
        row = con.execute("SELECT th_new, th_old FROM sources WHERE zh=?", (t,)).fetchone()
        if row:
            if row[0]:
                cands.setdefault(row[0], "DB exact row")
            if row[1]:
                cands.setdefault(row[1], "old official Thai")
        texts = [r[0] for r in con.execute(
            "SELECT th_new FROM sources WHERE status='done' AND instr(zh, ?) > 0 LIMIT 3000", (t,))]
        counts = {c: sum(c in x for x in texts) for c in cands}
        print(f"{t}  ({len(texts)} finished texts contain it)")
        for c, why in sorted(cands.items(), key=lambda kv: -counts[kv[0]]):
            print(f"   {counts[c]:5}  {c}   [{why}]")
        if t in series:
            pick = series[t]["th"]
        elif t in gloss and gloss[t]["th"] and gloss[t]["status"] == "approved":
            pick = gloss[t]["th"]
        elif cands:
            pick = max(cands, key=lambda c: counts[c])
        else:
            pick = (tl(t) if tl else "?") + "   (new name: Mandarin transliteration)"
        print(f"   -> use: {pick}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
