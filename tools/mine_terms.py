#!/usr/bin/env python3
"""
Phase 2 — mine glossary candidates from work/wwm.db.

A candidate is a short Chinese string (2-10 CJK chars, optional ·) that is
either a source text of its own (a name / label in the game) or appears inside
【】「」《》 brackets. For each candidate we count how many *other* source texts
contain it (df) and how many game keys that represents (occ), so terms that
recur across the game rank first — those are the ones that must be translated
the same way everywhere.

Output: work/glossary/candidates.tsv (UTF-8, tab separated)
"""
import collections
import re
import sqlite3
import sys
import time
from pathlib import Path

from pypinyin import Style, lazy_pinyin

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "work" / "wwm.db"
OUT = ROOT / "work" / "glossary" / "candidates.tsv"

CJK = r"一-鿿"
TERM_RE = re.compile(rf"^[{CJK}·]{{2,10}}$")
BRACKET_RE = re.compile(rf"[【「《]([{CJK}·]{{2,10}})[】」》]")
MAXLEN = 10


def norm_en(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def guess_type(zh, en):
    if not en:
        return "unknown"
    py = "".join(lazy_pinyin(zh.replace("·", "")))
    e = norm_en(en)
    if e == py:
        return "translit"                       # en is pure pinyin -> transliterated name
    if py and (e.startswith(py) or e.endswith(py) or (len(py) >= 4 and py in e)):
        return "translit_part"                  # name + title, e.g. "Elder Lu"
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", en)
    if len(words) >= 2 and all(w[0].isupper() or w.lower() in {"of", "the", "and", "in", "on", "to", "a"} for w in words):
        return "proper"                         # Title Case multi-word -> named thing
    return "generic"


def main():
    t0 = time.time()
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT src_id, zh, en, n_keys FROM sources WHERE zh NOT LIKE '@%'").fetchall()
    print(f"{len(rows):,} source texts")

    cands = {}            # term -> (src_id or None, en, self_keys)
    from_bracket = collections.Counter()
    for sid, zh, en, nk in rows:
        if TERM_RE.match(zh):
            cands[zh] = (sid, en, nk)
        for m in BRACKET_RE.finditer(zh):
            from_bracket[m.group(1)] += 1
    for t in from_bracket:
        cands.setdefault(t, (None, None, 0))
    print(f"{len(cands):,} candidates ({len(from_bracket):,} bracketed)  [{time.time()-t0:.0f}s]")

    df = collections.Counter()
    occ = collections.Counter()
    cset = set(cands)
    for sid, zh, en, nk in rows:
        found = set()
        n = len(zh)
        for i in range(n):
            for L in range(2, min(MAXLEN, n - i) + 1):
                s = zh[i:i + L]
                if s in cset and s != zh:
                    found.add(s)
        for s in found:
            df[s] += 1
            occ[s] += nk
    print(f"substring scan done  [{time.time()-t0:.0f}s]")

    # official Thai renderings of each candidate that is a source text
    th_var = {}
    for sid, th, c in con.execute(
            "SELECT e.src_id, e.th_old, count(*) FROM entries e JOIN sources s USING(src_id) "
            "WHERE length(s.zh) <= 10 GROUP BY 1, 2"):
        th_var.setdefault(sid, []).append((c, th))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("zh\ttype\tdf\tocc\tself_keys\tbracketed\ten\tpinyin\tth_top\tth_variants\n")
        ranked = sorted(cands.items(), key=lambda kv: -(occ[kv[0]] + kv[1][2]))
        for zh, (sid, en, nk) in ranked:
            if df[zh] < 2 and from_bracket[zh] < 2:
                continue  # not reused anywhere -> not a glossary concern
            vars_ = sorted(th_var.get(sid, []), reverse=True)
            th_top = vars_[0][1] if vars_ else ""
            var_s = " / ".join(f"{t}({c})" for c, t in vars_[:4])
            f.write("\t".join(str(x).replace("\t", " ").replace("\n", "\\n") for x in (
                zh, guess_type(zh, en), df[zh], occ[zh], nk, from_bracket[zh], en or "",
                " ".join(lazy_pinyin(zh, style=Style.TONE)), th_top, var_s)) + "\n")
            kept += 1
    print(f"wrote {kept:,} candidates -> {OUT}  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
