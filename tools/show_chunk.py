#!/usr/bin/env python3
"""Print a chunk compactly for in-chat translation: id, zh, terms, and a Mandarin
transliteration hint for short lines (names). Usage: python -I tools\\show_chunk.py NNNN"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translit import translit  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")
name = sys.argv[1]
for line in (ROOT / "work" / "queue" / f"{name}.tsv").read_text(encoding="utf-8").splitlines()[1:]:
    p = line.split("\t")
    if len(p) < 2:
        continue
    zh, terms = p[1], (p[4] if len(p) > 4 else "")
    hint = ""
    core = zh.replace("#R", "").replace("#E", "")
    if 2 <= len(core) <= 4 and all("一" <= ch <= "鿿" for ch in core):
        hint = " ~" + translit(core)
    print(f"{p[0]}\t{zh}\t{terms}{hint}")
