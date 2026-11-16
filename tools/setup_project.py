#!/usr/bin/env python3
"""
setup_project — get a fresh clone (or a wiped PC) ready to work. Run through setup.bat.

  1. find the game folder (Steam auto-detect, or ask) -> local.cfg
  2. copy the game's ORIGINAL Thai files to backup/original/ (refuses if the game has a mod installed)
  3. build work/wwm.db from the game files (tools/build_db.py)
  4. load all translations from translations/*.tsv into the DB

Safe to run again: steps that are already done are skipped.
"""
import random
import sqlite3
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = config.ROOT
BACKUP = ROOT / "backup" / "original"
DB = ROOT / "work" / "wwm.db"
PATCH_REL = Path("LocalData/Patch/HD/oversea/locale")
THAI = ["translate_words_map_th", "translate_words_map_th_diff"]


def run(*args):
    print(f"> python {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, "-I", *args], cwd=ROOT)
    if r.returncode:
        sys.exit(f"failed: {' '.join(args)}")


def ask_game():
    print("Could not find Where Winds Meet through Steam.")
    while True:
        p = input('Paste the game folder (the one with "Package" and "Engine" inside), or Enter to quit: ').strip().strip('"')
        if not p:
            sys.exit("cancelled")
        if config.is_game(p):
            config.save_game(p)
            return Path(p)
        print(f"  not a game folder: {p}")


def modded_share(game, name):
    """Share of sampled keys whose Thai text equals OUR translation (~0.15 original, ~1.0 modded)."""
    import wwmloc
    from translate import tsv_unesc
    loc = game / config.LOCALE_REL
    th_path = loc / name
    if not th_path.exists():
        return 0.0
    ours = {}
    for p in (ROOT / "translations").glob("*.tsv"):
        for line in p.read_text(encoding="utf-8").splitlines()[1:]:
            z, t = line.split("\t", 1)
            ours[tsv_unesc(z)] = tsv_unesc(t)
    zh = dict(wwmloc.iter_entries(wwmloc.read_container(loc / "translate_words_map_zh_cn")[1]))
    for d in (loc / "translate_words_map_zh_cn_diff", game / PATCH_REL / "translate_words_map_zh_cn_diff"):
        if d.exists():
            zh.update({k: v for k, v in wwmloc.iter_entries(wwmloc.read_container(d)[1]) if v != b"\xff"})
    th = dict(wwmloc.iter_entries(wwmloc.read_container(th_path)[1]))
    keys = [k for k in th if k in zh and th[k] != b"\xff"]
    random.seed(0)
    hit = tot = 0
    for k in random.sample(keys, min(5000, len(keys))):
        mine = ours.get(zh[k].decode("utf-8", "replace"))
        if mine is not None:
            tot += 1
            hit += th[k].decode("utf-8", "replace") == mine
    return hit / tot if tot else 0.0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        import pypinyin  # noqa: F401
        import zstandard  # noqa: F401
    except ImportError as e:
        sys.exit(f"missing Python package ({e.name}) - run: python -m pip install -r requirements.txt")

    print("[1/4] Game folder")
    game = config.game_dir(required=False) or ask_game()
    print(f"  {game}")

    print("[2/4] Original Thai files -> backup\\original")
    if (BACKUP / "Package" / THAI[0]).exists():
        print("  already there - skipped")
    else:
        for name in THAI:
            share = modded_share(game, name)
            print(f"  {name}: {share:.0%} of sampled lines equal our translation")
            if share > 0.6:
                sys.exit("\nThe game has the Thai mod installed, so its files are not the originals.\n"
                         "Restore them first: Steam > right-click the game > Properties > Installed Files >\n"
                         "Verify integrity of game files (or run uninstall.bat of the player kit), then run setup.bat again.")
        (BACKUP / "Package").mkdir(parents=True, exist_ok=True)
        copied = []
        for name in THAI:
            src = game / config.LOCALE_REL / name
            if src.exists():
                shutil.copy2(src, BACKUP / "Package" / name)
                copied.append(BACKUP / "Package" / name)
        patch = game / PATCH_REL / "translate_words_map_th_diff"
        if patch.exists():
            (BACKUP / "LocalData").mkdir(parents=True, exist_ok=True)
            shutil.copy2(patch, BACKUP / "LocalData" / patch.name)
            copied.append(BACKUP / "LocalData" / patch.name)
        import update_game
        (BACKUP / "SHA256.txt").write_text(
            "".join(f"{update_game.sha(p)} *{p.relative_to(ROOT).as_posix()}\n" for p in sorted(copied)), encoding="utf-8")
        print(f"  copied {len(copied)} files")

    print("[3/4] Database work\\wwm.db")
    fresh = not DB.exists()
    if fresh:
        DB.parent.mkdir(parents=True, exist_ok=True)
        run("tools/build_db.py", str(game))
        import update_game  # record zh/en hashes so update_game.py check can spot game updates
        import json
        con = sqlite3.connect(DB)
        con.execute("INSERT OR REPLACE INTO meta VALUES ('file_hashes', ?)",
                    (json.dumps({str(p): update_game.sha(p) for p in update_game.TRACKED if "_th" not in p.name}),))
        con.commit()
        con.close()
    else:
        print("  already there - skipped")

    print("[4/4] Translations from git -> database")
    run("tools/export_translations.py", "import" if fresh else "sync")

    print("\nReady. Next: build_mod.bat builds the mod and installs it into the game.")


if __name__ == "__main__":
    main()
