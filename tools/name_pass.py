#!/usr/bin/env python3
"""
name_pass — make proper names consistent using glossary/series_names.tsv.

Every row `zh  th  variants` means: in any translation whose Chinese text contains `zh`,
replace each forbidden variant (`a|b|c`, longest first) with `th`.
Applies to finished translations in work/wwm.db and to translated queue chunks
(work/queue/NNNN.out.tsv) that are not imported yet.

    python -I tools/name_pass.py                 dry run: show what would change
    python -I tools/name_pass.py --apply         change DB + queue files (back up the DB first!)
    python -I tools/name_pass.py --from 双元     only rules from this zh row to the end
                                                 (use after appending new rows)
    python -I tools/name_pass.py --show 30       print up to 30 example changes

After --apply, run build_mod.bat (it re-exports translations/ and rebuilds the game files).
A second run should report 0 changes.
"""
import argparse
import csv
import datetime
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "work" / "wwm.db"
QUEUE = ROOT / "work" / "queue"
SERIES = ROOT / "glossary" / "series_names.tsv"


def load_rules(start_zh=None):
    rows = list(csv.reader(SERIES.open(encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:]
    if start_zh:
        zhs = [r[0] for r in rows]
        if start_zh not in zhs:
            sys.exit(f"--from {start_zh}: not a zh entry in {SERIES.name}")
        rows = rows[zhs.index(start_zh):]
    rules = []
    for r in rows:
        if len(r) > 2 and r[2].strip():
            bads = sorted((b for b in r[2].split("|") if b and b not in r[1]), key=len, reverse=True)
            if bads:
                rules.append((r[0], r[1], bads))
    return rules


THAI = "฀-๿"


def fix(rules, zh, th):
    n = 0
    for z, good, bads in rules:
        if z in zh:
            for b in bads:
                if b in th:
                    n += th.count(b)
                    th = th.replace(b, good)
                    if re.match(r"[A-Za-z]", good):  # English term: keep a space from Thai letters
                        th = re.sub(f"(?<=[{THAI}]){re.escape(good)}", " " + good, th)
                    if re.search(r"[A-Za-z]$", good):
                        th = re.sub(f"{re.escape(good)}(?=[{THAI}])", good + " ", th)
    return th, n


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="apply series_names.tsv to finished translations")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    ap.add_argument("--from", dest="start", help="only rules from this zh row onward")
    ap.add_argument("--show", type=int, default=10, help="example changes to print")
    a = ap.parse_args()

    rules = load_rules(a.start)
    shown = 0

    def example(zh, old, new):
        nonlocal shown
        if shown < a.show:
            print(f"  {zh[:30]!r}\n    - {old[:80]!r}\n    + {new[:80]!r}")
            shown += 1

    con = sqlite3.connect(DB)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    texts = reps = 0
    for sid, zh, th in con.execute("SELECT src_id, zh, th_new FROM sources WHERE th_new IS NOT NULL AND th_new != ''").fetchall():
        new, n = fix(rules, zh, th)
        if n:
            texts += 1
            reps += n
            example(zh, th, new)
            if a.apply:
                con.execute("UPDATE sources SET th_new=?, updated_at=? WHERE src_id=?", (new, now, sid))
    print(f"rules {len(rules)} | DB texts changed {texts}, replacements {reps}")

    files = 0
    for out in sorted(QUEUE.glob("*.out.tsv")):
        src = QUEUE / out.name.replace(".out.tsv", ".tsv")
        if not src.exists() or (QUEUE / out.name.replace(".out.tsv", ".imported")).exists():
            continue  # imported chunks are already covered by the DB pass
        zh = {p[0]: p[1] for p in (l.split("\t") for l in src.read_text(encoding="utf-8-sig").splitlines()[1:]) if len(p) > 1}
        lines = out.read_text(encoding="utf-8-sig").split("\n")
        changed = 0
        for k, line in enumerate(lines[1:], 1):
            p = line.split("\t")
            if len(p) > 1 and p[0] in zh:
                p[1], n = fix(rules, zh[p[0]], p[1])
                if n:
                    changed += n
                    lines[k] = "\t".join(p)
        if changed:
            files += 1
            if a.apply:
                out.write_text("\n".join(lines), encoding="utf-8", newline="")
    print(f"queue files changed {files} (not yet imported)")

    if a.apply:
        con.commit()
        print("applied - now run build_mod.bat")
    else:
        print("dry run - add --apply to write")


if __name__ == "__main__":
    main()
