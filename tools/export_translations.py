#!/usr/bin/env python3
"""
export_translations — keep the translations in git as plain TSV.

    python -I tools/export_translations.py export   # work/wwm.db -> translations/<category>.tsv
    python -I tools/export_translations.py import   # translations/*.tsv -> work/wwm.db (match by zh)

Files: translations/<category>.tsv, header `zh<TAB>th`, one row per unique Chinese text,
sorted by zh so diffs stay small. Escapes as in the queue files: \\n \\t \\r \\\\.

`import` is for a fresh machine/DB (after tools/build_db.py): every source whose zh appears
in the TSVs gets th_new + status done. It overwrites th_new of matching rows, so back up first.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate import tsv_esc, tsv_unesc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "work" / "wwm.db"
OUT = ROOT / "translations"


def export(con):
    OUT.mkdir(exist_ok=True)
    rows = con.execute("SELECT category, zh, th_new FROM sources "
                       "WHERE status='done' AND th_new IS NOT NULL AND th_new != ''").fetchall()
    by_cat = {}
    for cat, zh, th in rows:
        by_cat.setdefault(cat or "other", []).append((zh, th))
    for old in OUT.glob("*.tsv"):
        if old.stem not in by_cat:
            old.unlink()
    for cat, items in sorted(by_cat.items()):
        items.sort()
        p = OUT / f"{cat}.tsv"
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("zh\tth\n")
            for zh, th in items:
                f.write(f"{tsv_esc(zh)}\t{tsv_esc(th)}\n")
        print(f"{p.relative_to(ROOT)}: {len(items):,} rows, {p.stat().st_size / 1e6:.1f} MB")


def import_(con):
    n = miss = 0
    for p in sorted(OUT.glob("*.tsv")):
        lines = p.read_text(encoding="utf-8").splitlines()[1:]
        for line in lines:
            zh, th = (tsv_unesc(x) for x in line.split("\t", 1))
            cur = con.execute("UPDATE sources SET th_new=?, status='done', model='git' WHERE zh=?", (th, zh))
            if cur.rowcount:
                n += 1
            else:
                miss += 1
        print(f"{p.name}: {len(lines):,} rows")
    con.commit()
    print(f"applied {n:,}; {miss:,} not in this game version's DB")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "import"])
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    export(con) if a.cmd == "export" else import_(con)


if __name__ == "__main__":
    main()
