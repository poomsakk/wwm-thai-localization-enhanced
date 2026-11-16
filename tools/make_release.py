#!/usr/bin/env python3
"""
make_release — pack the player kit into a release zip.

    python -I tools/make_release.py [--version 2026.11.16] [--repo owner/name]

Inputs
  release/                       install.bat, play.bat, uninstall.bat, wwm-thai.ps1, README.txt
  work/build/translate_words_map_th[_diff]          mod files (run build_mod.bat first)
  backup/original/Package/translate_words_map_th[_diff]   game originals they were built from

Outputs (dist/<version>/)
  WWM-Thai-<version>.zip   the kit; data/manifest.txt inside lists all SHA256s
  manifest.txt             same + zip_name + zip_sha256  -> upload BOTH to the GitHub Release
                           (play.bat reads manifest.txt to find the release matching the game)

--repo writes the GitHub "owner/name" into the zipped wwm-thai.ps1 (enables auto-update).
"""
import argparse
import datetime
import hashlib
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "release"
BUILD = ROOT / "work" / "build"
ORIG = ROOT / "backup" / "original" / "Package"
GAME = config.game_dir()
FILES = ["translate_words_map_th", "translate_words_map_th_diff"]
KIT_FILES = ["install.bat", "play.bat", "uninstall.bat", "wwm-thai.ps1", "README.txt"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def kit_bytes(name, repo):
    data = (KIT / name).read_bytes()
    if name.endswith(".bat"):  # cmd needs CRLF
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if name == "wwm-thai.ps1":
        text = data.decode("utf-8-sig")
        if repo:
            text, n = re.subn(r"^\$Repo(\s*)= ''", lambda m: f"$Repo{m.group(1)}= '{repo}'", text, count=1, flags=re.M)
            if n != 1:
                sys.exit("could not set $Repo in wwm-thai.ps1")
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        data = "\ufeff".encode() + text.encode("utf-8")  # Windows PowerShell 5.1 needs a BOM for Thai text
    if name == "README.txt":
        data = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    return data


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", help="mod version, 2-4 numbers (default: today, e.g. 2026.11.16)")
    ap.add_argument("--repo", default="poomsakk/wwm-thai-localization-enhanced",
                    help='GitHub "owner/name" for auto-update ("" = off)')
    a = ap.parse_args()

    today = datetime.date.today()
    ver = a.version or f"{today.year}.{today.month}.{today.day}"
    if not re.fullmatch(r"\d+(\.\d+){1,3}", ver):
        sys.exit(f"bad version {ver!r}: use 2-4 numbers like 2026.11.16 or 2026.11.16.1")
    if a.repo and not re.fullmatch(r"[\w.-]+/[\w.-]+", a.repo):
        sys.exit(f"bad --repo {a.repo!r}: use owner/name")
    for p in [KIT / n for n in KIT_FILES] + [BUILD / f for f in FILES] + [ORIG / f for f in FILES]:
        if not p.exists():
            sys.exit(f"missing {p}")

    bv = GAME / "Engine" / "Binaries" / "Win64r" / "Built.version"
    man = {"mod_version": ver,
           "game_build": bv.read_text(encoding="utf-8", errors="replace").strip() if bv.exists() else "unknown"}
    for f in FILES:
        man[f"orig_{f}"] = sha(ORIG / f)
        man[f"mod_{f}"] = sha(BUILD / f)
        if man[f"orig_{f}"] == man[f"mod_{f}"]:
            sys.exit(f"{f}: build is identical to the original - run build_mod.bat first")
    for f in FILES:  # warn if the installed game is neither original nor this build
        g = GAME / "Package" / "HD" / "oversea" / "locale" / f
        if g.exists() and sha(g) not in (man[f"orig_{f}"], man[f"mod_{f}"]):
            print(f"WARNING: game's {f} matches neither backup/original nor work/build "
                  f"- game updated? run update_game.bat + build_mod.bat first")
    man_text = "".join(f"{k}={v}\n" for k, v in man.items())

    name = f"WWM-Thai-{ver}"
    out = ROOT / "dist" / ver
    out.mkdir(parents=True, exist_ok=True)
    zp = out / f"{name}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in KIT_FILES:
            z.writestr(f"{name}/{n}", kit_bytes(n, a.repo))
        for f in FILES:  # already zstd-compressed: store as-is
            z.write(BUILD / f, f"{name}/data/{f}", compress_type=zipfile.ZIP_STORED)
        z.writestr(f"{name}/data/manifest.txt", man_text)
    (out / "manifest.txt").write_text(man_text + f"zip_name={zp.name}\nzip_sha256={sha(zp)}\n",
                                      encoding="utf-8", newline="\n")
    print(man_text, end="")
    print(f"repo={a.repo or '(none: auto-update off)'}")
    print(f"-> {zp}  ({zp.stat().st_size / 1e6:.1f} MB)")
    print(f"-> {out / 'manifest.txt'}")


if __name__ == "__main__":
    main()
