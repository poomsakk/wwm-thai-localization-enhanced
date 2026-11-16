#!/usr/bin/env python3
"""
Make fixed names consistent in not-yet-imported work/queue/NNNN.out.tsv files.

glossary/series_names.tsv: zh <TAB> preferred th <TAB> variants (| separated).
A variant is replaced only on lines whose Chinese source contains that zh term,
and only where the preferred rendering is not already present.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "work" / "queue"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with open(ROOT / "glossary" / "series_names.tsv", encoding="utf-8") as f:
        rules = [(r["zh"], r["th"], [v for v in r["variants"].split("|") if v])
                 for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)]
    total = 0
    for out in sorted(Q.glob("*.out.tsv")):
        name = out.name.split(".")[0]
        if (Q / f"{name}.imported").exists() or not (Q / f"{name}.tsv").exists():
            continue
        src = {}
        for line in (Q / f"{name}.tsv").read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) > 1:
                src[parts[0]] = parts[1]
        lines = out.read_text(encoding="utf-8").split("\n")
        changed = 0
        for i, line in enumerate(lines):
            sid, sep, th = line.partition("\t")
            zh = src.get(sid)
            if not sep or zh is None:
                continue
            new = th
            for term, pref, variants in rules:
                if term in zh and pref not in new:
                    for v in variants:
                        if v in new:
                            new = new.replace(v, pref)
                            break
            if new != th:
                lines[i] = f"{sid}\t{new}"
                changed += 1
        if changed:
            out.write_text("\n".join(lines), encoding="utf-8")
            print(f"{name}: {changed} lines normalised")
            total += changed
    print(f"total {total} lines")


if __name__ == "__main__":
    main()
