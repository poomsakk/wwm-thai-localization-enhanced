#!/usr/bin/env python3
"""
export_translations — keep the translations in git (translations/*.tsv) in step with work/wwm.db.

    python -I tools/export_translations.py export   DB -> translations/<category>.tsv
    python -I tools/export_translations.py sync     bring changes from git (pull / merged PR) into the DB
    python -I tools/export_translations.py import   translations/*.tsv -> DB for every row (TSV wins)

Files: translations/<category>.tsv, header `zh<TAB>th`, one row per unique Chinese text,
sorted by zh so diffs stay small. Escapes as in the queue files: \\n \\t \\r \\\\.

How sync knows what changed: every export/import/sync leaves a copy of the TSVs in
work/translations_base/ (local, not in git). sync compares translations/ with that copy;
only rows that changed there (= came from git) are written to the DB, so local DB work on
other rows is kept. If a row changed on both sides, the git version wins and it is listed.
build_mod.bat runs `sync` before importing chunks and `export` after.
"""
import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate import tsv_esc, tsv_unesc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "work" / "wwm.db"
OUT = ROOT / "translations"
BASE = ROOT / "work" / "translations_base"


def read_dir(d):
    t = {}
    for p in sorted(d.glob("*.tsv")):
        for line in p.read_text(encoding="utf-8").splitlines()[1:]:
            zh, th = line.split("\t", 1)
            t[tsv_unesc(zh)] = tsv_unesc(th)
    return t


def db_done(con):
    return dict(con.execute("SELECT zh, th_new FROM sources "
                            "WHERE status='done' AND th_new IS NOT NULL AND th_new != ''"))


def save_base():
    if BASE.exists():
        shutil.rmtree(BASE)
    shutil.copytree(OUT, BASE)


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
    save_base()


def apply_rows(con, rows):
    """rows: {zh: th}. Returns (applied, not_in_db)."""
    n = miss = 0
    for zh, th in rows.items():
        cur = con.execute("UPDATE sources SET th_new=?, status='done', model='git' WHERE zh=?", (th, zh))
        if cur.rowcount:
            n += 1
        else:
            miss += 1
    con.commit()
    return n, miss


def import_(con):
    n, miss = apply_rows(con, read_dir(OUT))
    save_base()
    print(f"applied {n:,}; {miss:,} not in this game version's DB")


def sync(con):
    tsv = read_dir(OUT)
    if not BASE.exists():
        db = db_done(con)
        diff = [z for z in set(tsv) | set(db) if tsv.get(z) != db.get(z)]
        if diff:
            sys.exit(f"sync: no record of the last export and translations/ differs from the DB in {len(diff):,} rows.\n"
                     f"  translations/ is newer (fresh clone / pull) -> export_translations.py import\n"
                     f"  the DB is newer                             -> export_translations.py export")
        save_base()
        print("sync: translations/ matches the DB")
        return
    base = read_dir(BASE)
    incoming = {z: t for z, t in tsv.items() if base.get(z) != t}
    removed = [z for z in base if z not in tsv]
    if not incoming and not removed:
        print("sync: no changes from git")
        return
    db = db_done(con)
    conflicts = [z for z in incoming if z in db and db[z] != base.get(z, db[z])]
    n, miss = apply_rows(con, incoming)
    print(f"sync: {n:,} rows from git applied to the DB ({miss:,} not in this game version)")
    for z in conflicts[:20]:
        print(f"  also changed locally, git version used: {z[:40]!r}")
    if len(conflicts) > 20:
        print(f"  ... {len(conflicts) - 20} more")
    if removed:
        print(f"  {len(removed):,} rows were deleted in git - the DB keeps them (they come back on export)")
    save_base()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "sync", "import"])
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    {"export": export, "sync": sync, "import": import_}[a.cmd](con)


if __name__ == "__main__":
    main()
