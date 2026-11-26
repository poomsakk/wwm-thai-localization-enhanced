#!/usr/bin/env python3
"""
config — where the game is installed on THIS machine (one place for every tool and .bat).

Lookup order:
  1. environment variable WWM_GAME
  2. local.cfg in the project root (line `game=D:\\...\\Where Winds Meet`; not in git)
  3. auto-detect from Steam (registry + steamapps/libraryfolders.vdf), then saved to local.cfg

    python -I tools/config.py game          print the game folder (exit 1 if not found)
    python -I tools/config.py set "PATH"    save a game folder to local.cfg
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "local.cfg"
GAME_NAME = "Where Winds Meet"
LOCALE_REL = Path("Package/HD/oversea/locale")
PATCH_REL = Path("LocalData/Patch/HD/oversea/locale")   # the game's own launcher (Lite / Standard) keeps all text here


def locale_file(game, name):
    """A main locale file: Package (Steam) if there, else LocalData\\Patch (launcher install)."""
    p = Path(game) / LOCALE_REL / name
    return p if p.exists() else Path(game) / PATCH_REL / name


def is_game(p):
    # the Chinese source text is needed to work on the translation
    return bool(p) and locale_file(p, "translate_words_map_zh_cn").exists()


def read_cfg():
    cfg = {}
    if CFG.exists():
        for line in CFG.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"')
    return cfg


def save_game(path):
    cfg = read_cfg()
    cfg["game"] = str(Path(path))
    CFG.write_text("# machine-specific settings (not in git)\n" + "".join(f"{k}={v}\n" for k, v in cfg.items()),
                   encoding="utf-8")


def steam_libraries():
    libs = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam = Path(winreg.QueryValueEx(k, "SteamPath")[0])
        libs.append(steam)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace")):
                libs.append(Path(m.group(1).replace("\\\\", "\\")))
    except OSError:
        pass
    return libs


def detect():
    for lib in steam_libraries():
        p = lib / "steamapps" / "common" / GAME_NAME
        if is_game(p):
            return p
    return None


def game_dir(required=True):
    """The game folder as a Path, or None / exit when it cannot be found."""
    for cand in (os.environ.get("WWM_GAME"), read_cfg().get("game")):
        if is_game(cand):
            return Path(cand)
    p = detect()
    if p:
        save_game(p)
        return p
    if required:
        sys.exit(f"Game folder not found. Run setup.bat, or put a line  game=<folder of {GAME_NAME}>  in {CFG}")
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 2 and sys.argv[1] == "game":
        p = game_dir(required=False)
        if not p:
            sys.exit(1)
        print(p)
    elif len(sys.argv) == 3 and sys.argv[1] == "set":
        p = Path(sys.argv[2].strip('"'))
        if not is_game(p):
            sys.exit(f"not a {GAME_NAME} folder (no translate_words_map_zh_cn in {LOCALE_REL} or {PATCH_REL}): {p}")
        save_game(p)
        print(f"saved: {p}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
