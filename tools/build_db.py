#!/usr/bin/env python3
"""
Phase 1 — build the working database work/wwm.db from the game's locale files.

Tables
  sources  one row per unique Chinese source text (what we actually translate)
           src_id, zh, en (most common), th_old (most common), n_keys,
           n_th_variants (how many different official Thai renderings),
           category, tags, zh_len, priority, th_new, status
  entries  one row per game key: key, src_id, en, th_old, origin
           origin = main | diff (only in patch _diff) | main+diff

Effective text per language = main file, overridden by the patch _diff
(LocalData\\Patch) when present, else the package _diff; 0xFF in a _diff means
"no override" and is ignored.

Usage: python build_db.py [game_dir]
"""
import collections
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wwmloc  # noqa: E402
import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "work" / "wwm.db"
GAME = Path(sys.argv[1]) if len(sys.argv) > 1 else config.game_dir()
PKG = GAME / "Package/HD/oversea/locale"
PATCH = GAME / "LocalData/Patch/HD/oversea/locale"
TOMB = b"\xff"

# ------------------------------------------------------------------ loading
def load_map(path):
    return dict(wwmloc.iter_entries(wwmloc.read_container(path)[1])) if path.exists() else {}


BACKUP = ROOT / "backup" / "original"  # pristine copies of files we may have modded


def effective(lang):
    """Layers, lowest first: Package main <- Package _diff <- LocalData\\Patch _diff (later wins,
    0xFF = no override) - the same rule as update_game.py. Each file comes from backup\\original
    when it is there (the game's Thai files may be our mod), else from the game."""
    def path(sub, game_dir, name):
        b = BACKUP / sub / name
        return b if b.exists() else game_dir / name
    main = load_map(path("Package", PKG, f"translate_words_map_{lang}"))
    diff = {}
    for sub, game_dir in (("Package", PKG), ("LocalData", PATCH)):
        diff.update({k: v for k, v in load_map(path(sub, game_dir, f"translate_words_map_{lang}_diff")).items()
                     if v != TOMB})
    return main, diff


def dec(b):
    return b.decode("utf-8", "replace") if b is not None else None


# ------------------------------------------------------------------ analysis
TAG_RES = {
    "color": re.compile(r"#[A-Za-z]"),            # #Y ... #E
    "brace": re.compile(r"\{[^{}]{0,40}\}"),      # {0} {name}
    "printf": re.compile(r"%(?:\d+\$)?[-+ 0#]*\d*(?:\.\d+)?[sdif]"),
    "angle": re.compile(r"<[^<>]{1,60}>"),        # <...> markup / stage directions
    "newline": re.compile(r"\n"),
    "gender": re.compile(r"\|"),                  # male|female variants
}
PRONOUNS = re.compile(r"我|你|您|咱|吾|俺|在下|老夫|本座|本官|贫僧|贫道|小的|小人|妾身|奴家|尔等|汝")
SENT_PUNCT = re.compile(r"[。！？!?…，,；;：“”\"「」]")


def tags_of(s):
    return ",".join(k for k, r in TAG_RES.items() if r.search(s))


def strip_tags(s):
    s = re.sub(r"#[A-Za-z]", "", s)
    return re.sub(r"\{[^{}]*\}|<[^<>]*>|%[sdif]", "", s)


def categorize(zh):
    core = strip_tags(zh).strip()
    if not core:
        # a whole line in <...> is visible text (cutscene inner voice, stage direction), not a tag:
        # categorize by what is inside the brackets
        core = re.sub(r"[<>]", "", strip_tags(re.sub(r"<([^<>]*)>", r"\1", zh))).strip()
    n = len(core)
    if n == 0:
        return "empty"
    if n <= 4 and not SENT_PUNCT.search(core):
        return "ui_short"
    if n <= 15 and not SENT_PUNCT.search(core):
        return "label"
    if PRONOUNS.search(core) or re.search(r"[！？!?]", core):
        return "dialogue" if n <= 200 else "long_text"
    return "description" if n <= 200 else "long_text"


# lower = translate earlier; refined by how often a string is used
CAT_PRIORITY = {"ui_short": 1, "label": 2, "description": 3, "dialogue": 4, "long_text": 5, "empty": 9}

# ------------------------------------------------------------------ build
def main():
    t0 = time.time()
    print("loading locale files ...")
    th_main, th_diff = effective("th")
    zh_main, zh_diff = effective("zh_cn")
    en_main, en_diff = effective("en")

    keys = set(th_main) | set(th_diff)
    print(f"  th keys: {len(keys):,} (main {len(th_main):,}, diff {len(th_diff):,})  [{time.time()-t0:.0f}s]")

    def pick(main, diff, k):
        return diff.get(k, main.get(k))

    groups = collections.defaultdict(list)  # source text -> [(key, en, th)]
    origin = {}
    for k in keys:
        zh = pick(zh_main, zh_diff, k)
        en = pick(en_main, en_diff, k)
        th = pick(th_main, th_diff, k)
        # a few keys have no Chinese; fall back to English as the source text
        src = dec(zh) if zh else ("@en:" + dec(en) if en else "@th:" + dec(th))
        groups[src].append((k, dec(en), dec(th)))
        origin[k] = "main+diff" if (k in th_main and k in th_diff) else ("main" if k in th_main else "diff")

    print(f"  unique source texts: {len(groups):,}  [{time.time()-t0:.0f}s]")

    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(
        """
        CREATE TABLE sources(
            src_id INTEGER PRIMARY KEY, zh TEXT NOT NULL UNIQUE, en TEXT, th_old TEXT,
            n_keys INTEGER, n_th_variants INTEGER, category TEXT, tags TEXT, zh_len INTEGER,
            priority INTEGER, th_new TEXT, status TEXT DEFAULT 'todo', note TEXT);
        CREATE TABLE entries(
            key TEXT PRIMARY KEY, src_id INTEGER REFERENCES sources, en TEXT, th_old TEXT, origin TEXT);
        CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
        """
    )
    src_rows, ent_rows = [], []
    for sid, (zh, items) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1])), 1):
        en_c = collections.Counter(e for _, e, _ in items if e)
        th_c = collections.Counter(t for _, _, t in items if t)
        cat = categorize(zh)
        prio = CAT_PRIORITY[cat]
        src_rows.append((sid, zh, en_c.most_common(1)[0][0] if en_c else None,
                         th_c.most_common(1)[0][0] if th_c else None, len(items), len(th_c),
                         cat, tags_of(zh), len(strip_tags(zh)), prio))
        for k, e, t in items:
            ent_rows.append((k.hex(), sid, e, t, origin[k]))
    con.executemany("INSERT INTO sources(src_id,zh,en,th_old,n_keys,n_th_variants,category,tags,zh_len,priority)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)", src_rows)
    con.executemany("INSERT INTO entries VALUES (?,?,?,?,?)", ent_rows)
    con.executescript("CREATE INDEX ix_entries_src ON entries(src_id); CREATE INDEX ix_src_cat ON sources(category);")
    con.executemany("INSERT INTO meta VALUES (?,?)", [
        ("built_at", time.strftime("%Y-%m-%d %H:%M:%S")), ("game_dir", str(GAME)),
        ("built_version", (GAME / "Engine/Binaries/Win64r/Built.version").read_text(errors="replace").strip()
         if (GAME / "Engine/Binaries/Win64r/Built.version").exists() else ""),
    ])
    con.commit()
    con.close()
    print(f"wrote {DB} ({DB.stat().st_size/1e6:.0f} MB) [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
