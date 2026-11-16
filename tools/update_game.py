#!/usr/bin/env python3
"""
update_game — bring the project up to date after a game update, WITHOUT losing translations.

    python -I tools/update_game.py check     exit 0 = nothing to do, 1 = game updated (run apply)
    python -I tools/update_game.py apply     back up the new originals and update work/wwm.db
    python -I tools/update_game.py apply --dry-run   only report what would change

What `apply` does
  1. Detects which locale files changed (game file differs from backup\\original AND from our
     last build in work\\build). Our own installed mod is never mistaken for a new original.
  2. Moves the old backup\\original to backup\\original_<date>_<version> and copies the new
     original Thai files from the game into backup\\original (build_mod.bat patches from it).
  3. Copies work\\wwm.db to work\\wwm.db.bak_<date> and updates it in place:
       - every game key is re-linked to its (possibly new) Chinese source text;
       - a key whose Chinese text already exists in the DB reuses that row, so its Thai
         translation carries over automatically;
       - Chinese text never seen before becomes a new source (status todo);
       - sources no game key uses any more and that were never translated -> status 'unused'
         (so they are not put into new chunks). Translated rows are kept as they are.
  4. Prints a report: keys added / removed / changed, new texts per category.
New texts are then chunked as usual, e.g. `translate.py chunks --category description`.
"""
import argparse
import collections
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wwmloc  # noqa: E402
import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "work" / "wwm.db"
BACKUP = ROOT / "backup" / "original"
BUILD = ROOT / "work" / "build"
GAME = config.game_dir()
PKG = GAME / "Package/HD/oversea/locale"
PATCH = GAME / "LocalData/Patch/HD/oversea/locale"
VERSION_FILE = GAME / "Engine/Binaries/Win64r/Built.version"
TOMB = b"\xff"
LANGS = ("th", "zh_cn", "en")

# the two Thai files we back up / patch:  (game path, backup path, our build output)
THAI_FILES = [
    (PKG / "translate_words_map_th", BACKUP / "Package/translate_words_map_th", BUILD / "translate_words_map_th"),
    (PKG / "translate_words_map_th_diff", BACKUP / "Package/translate_words_map_th_diff",
     BUILD / "translate_words_map_th_diff"),
    (PATCH / "translate_words_map_th_diff", BACKUP / "LocalData/translate_words_map_th_diff", None),
]
# source files whose content we track by hash (stored in wwm.db meta)
TRACKED = [PKG / f"translate_words_map_{l}" for l in LANGS] + \
          [PATCH / f"translate_words_map_{l}_diff" for l in LANGS] + \
          [PKG / f"translate_words_map_{l}_diff" for l in LANGS]


# ------------------------------------------------------------ helpers (same rules as build_db.py)
def sha(p):
    if not p or not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def game_version():
    return VERSION_FILE.read_text(errors="replace").strip() if VERSION_FILE.exists() else ""


def load_map(path):
    return dict(wwmloc.iter_entries(wwmloc.read_container(path)[1])) if path.exists() else {}


def effective(lang, backup):
    """Layers for one language, lowest first: Package main, Package _diff, LocalData\Patch _diff.
    A later layer overrides an earlier one; 0xFF in a _diff = no override. Thai is read from
    `backup` (the game copy may be our mod), zh/en from the game."""
    def path(sub, name, game_dir):
        b = backup / sub / name
        return b if b.exists() else game_dir / name
    main = load_map(path("Package", f"translate_words_map_{lang}", PKG))
    layers = []
    for sub, game_dir in (("Package", PKG), ("LocalData", PATCH)):
        layers.append({k: v for k, v in load_map(path(sub, f"translate_words_map_{lang}_diff", game_dir)).items()
                       if v != TOMB})
    return main, layers


def dec(b):
    return b.decode("utf-8", "replace") if b is not None else None


def analysis():
    """categorize / tags_of / strip_tags / CAT_PRIORITY from build_db (imported without running it)."""
    saved, sys.argv = sys.argv, sys.argv[:1]
    try:
        import build_db
    finally:
        sys.argv = saved
    return build_db


# ------------------------------------------------------------ change detection
def detect(con):
    """-> (changed_thai: [(game, backup)], changed_tracked: [path], reasons: [str])"""
    reasons, changed_thai = [], []
    for game, backup, build in THAI_FILES:
        g = sha(game)
        if g is None:
            continue
        if g == sha(backup):
            continue
        if build is not None and g == sha(build):
            continue  # that's our installed mod
        changed_thai.append((game, backup))
        reasons.append(f"new original: {game.relative_to(GAME)}")
    old = {}
    if con is not None:
        row = con.execute("SELECT v FROM meta WHERE k='file_hashes'").fetchone()
        old = json.loads(row[0]) if row else {}
    changed_tracked = []
    for p in TRACKED:
        if "_th" in p.name:
            continue  # Thai handled above (the game copy may be our mod)
        h = sha(p)
        if old and old.get(str(p)) != h:
            changed_tracked.append(p)
            reasons.append(f"changed: {p.relative_to(GAME)}")
    return changed_thai, changed_tracked, reasons, bool(old)


def cmd_check(a):
    con = sqlite3.connect(DB) if DB.exists() else None
    changed_thai, changed_tracked, reasons, has_hashes = detect(con)
    if changed_thai or changed_tracked:
        print("GAME UPDATED - run update_game.bat (tools\\update_game.py apply) before building:")
        for r in reasons:
            print("  " + r)
        return 1
    note = "" if has_hashes else " (zh/en not tracked yet - recorded on the next apply)"
    print("Locale files match the backup / our build - no update needed." + note)
    return 0


# ------------------------------------------------------------ apply
def cmd_apply(a):
    t0 = time.time()
    if not DB.exists():
        raise SystemExit(f"{DB} not found - run tools\\build_db.py first")
    con = sqlite3.connect(DB)
    changed_thai, changed_tracked, reasons, _ = detect(con)
    if not (changed_thai or changed_tracked) and not a.force:
        print("No game update detected - nothing to do (use --force to re-sync anyway).")
        return 0
    for r in reasons:
        print("  " + r)
    version = game_version()
    row = con.execute("SELECT v FROM meta WHERE k='built_version'").fetchone()
    old_version = row[0] if row and row[0] else "old"
    stamp = time.strftime("%Y%m%d_%H%M")

    # new Thai originals: read straight from the game (backup\original is replaced only after the DB step)
    staged = ROOT / "work" / "update_staging"
    if staged.exists():
        shutil.rmtree(staged)
    for game, backup in changed_thai:
        dst = staged / backup.relative_to(BACKUP)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(game, dst)
    for game, backup, _ in THAI_FILES:  # unchanged files: take the current backup copy
        dst = staged / backup.relative_to(BACKUP)
        if not dst.exists() and backup.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, dst)
    for game, backup in changed_thai:  # sanity check: the new file must parse
        wwmloc.cmd_verify(str(staged / backup.relative_to(BACKUP)))

    print("loading locale files ...")
    bd = analysis()
    maps = {l: effective(l, staged) for l in LANGS}
    th_main, th_layers = maps["th"]
    th_diff_keys = set().union(*th_layers)
    keys = set(th_main) | th_diff_keys
    print(f"  th keys: {len(keys):,}  [{time.time()-t0:.0f}s]")

    def pick(lang, k):
        m, layers = maps[lang]
        v = m.get(k)
        for d in layers:
            v = d.get(k, v)
        return v

    new_map = {}  # key hex -> (src text, en, th, origin)
    for k in keys:
        zh, en, th = pick("zh_cn", k), pick("en", k), pick("th", k)
        src = dec(zh) if zh else ("@en:" + dec(en) if en else "@th:" + dec(th))
        origin = "main+diff" if (k in th_main and k in th_diff_keys) else ("main" if k in th_main else "diff")
        new_map[k.hex()] = (src, dec(en), dec(th), origin)

    zh_to_id = dict(con.execute("SELECT zh, src_id FROM sources"))
    old_entries = dict(con.execute("SELECT key, src_id FROM entries"))
    id_to_zh = {v: z for z, v in zh_to_id.items()}

    # group new texts
    new_groups = collections.defaultdict(list)
    for key, (src, en, th, _) in new_map.items():
        if src not in zh_to_id:
            new_groups[src].append((en, th))
    added = [k for k in new_map if k not in old_entries]
    removed = [k for k in old_entries if k not in new_map]
    changed = [k for k in new_map if k in old_entries and id_to_zh.get(old_entries[k]) != new_map[k][0]]
    reused = sum(1 for k in added + changed if new_map[k][0] in zh_to_id)

    cat_count, cat_chars = collections.Counter(), collections.Counter()
    for zh in new_groups:
        c = bd.categorize(zh)
        cat_count[c] += 1
        cat_chars[c] += len(bd.strip_tags(zh))

    print("\n=== update report ===")
    print(f"game version: {old_version} -> {version}")
    print(f"keys: {len(new_map):,} now (was {len(old_entries):,}) | added {len(added):,} | "
          f"removed {len(removed):,} | Chinese text changed {len(changed):,}")
    print(f"added/changed keys that reuse an existing text (translation carries over): {reused:,}")
    print(f"NEW texts to translate: {len(new_groups):,} ({sum(cat_chars.values()):,} zh chars)")
    for c, n in cat_count.most_common():
        print(f"  {c:12} {n:7,} texts  {cat_chars[c]:9,} chars")

    if a.dry_run:
        shutil.rmtree(staged)
        print("\n--dry-run: nothing was changed.")
        return 0

    # ---- write: backups first
    db_bak = DB.with_name(f"wwm.db.bak_{stamp}")
    con.close()
    shutil.copy2(DB, db_bak)
    print(f"\nDB backup: {db_bak.name}")
    con = sqlite3.connect(DB)
    with con:
        next_id = (con.execute("SELECT max(src_id) FROM sources").fetchone()[0] or 0) + 1
        rows = []
        for zh, items in sorted(new_groups.items(), key=lambda kv: -len(kv[1])):
            en_c = collections.Counter(e for e, _ in items if e)
            th_c = collections.Counter(t for _, t in items if t)
            cat = bd.categorize(zh)
            rows.append((next_id, zh, en_c.most_common(1)[0][0] if en_c else None,
                         th_c.most_common(1)[0][0] if th_c else None, len(items), len(th_c), cat,
                         bd.tags_of(zh), len(bd.strip_tags(zh)), bd.CAT_PRIORITY[cat], f"new:{version}"))
            zh_to_id[zh] = next_id
            next_id += 1
        con.executemany("INSERT INTO sources(src_id,zh,en,th_old,n_keys,n_th_variants,category,tags,zh_len,"
                        "priority,note) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.execute("DELETE FROM entries")
        con.executemany("INSERT INTO entries VALUES (?,?,?,?,?)",
                        ((k, zh_to_id[src], en, th, o) for k, (src, en, th, o) in new_map.items()))
        con.execute("UPDATE sources SET n_keys=(SELECT count(*) FROM entries e WHERE e.src_id=sources.src_id)")
        unused = con.execute("UPDATE sources SET status='unused' WHERE n_keys=0 AND status IN ('todo','queued')").rowcount
        revived = con.execute("UPDATE sources SET status='todo' WHERE n_keys>0 AND status='unused'").rowcount
        hashes = {str(p): sha(p) for p in TRACKED if "_th" not in p.name}
        meta = [("updated_at", time.strftime("%Y-%m-%d %H:%M:%S")), ("built_version", version),
                ("file_hashes", json.dumps(hashes)),
                (f"update_{stamp}", json.dumps({"version": version, "added": len(added), "removed": len(removed),
                                                "changed": len(changed), "new_texts": len(new_groups)}))]
        con.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", meta)
    con.close()
    print(f"DB updated: +{len(rows):,} new sources, {unused:,} no longer used, {revived:,} back in use")

    # ---- swap the Thai backup (old one is kept)
    if changed_thai:
        old_dir = BACKUP.with_name(f"original_{old_version.replace('/', '_')}_replaced_{stamp}")
        shutil.move(str(BACKUP), str(old_dir))
        shutil.move(str(staged), str(BACKUP))
        lines = [f"{sha(p)} *{p.relative_to(ROOT).as_posix()}" for p in sorted(BACKUP.rglob("translate_words_map_*"))]
        (BACKUP / "SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"backup\\original = new game files (old copy kept in backup\\{old_dir.name})")
    else:
        shutil.rmtree(staged)
    print(f"\nDone in {time.time()-t0:.0f}s. Next: run build_mod.bat to install the mod on the new version.")
    if rows:
        print("New texts are status 'todo' - chunk them with e.g. "
              "`python -I tools/translate.py chunks --category ui_short` (see report above).")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    s = sub.add_parser("apply")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--force", action="store_true")
    a = p.parse_args()
    return {"check": cmd_check, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main() or 0)
