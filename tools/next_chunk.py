#!/usr/bin/env python3
"""
next_chunk — hand out queue chunks to parallel translators (e.g. subagents), lowest number first.

    python -I tools/next_chunk.py              claim the lowest waiting chunk -> prints NEXT=NNNN
    python -I tools/next_chunk.py 1578         check 1578; if 0 problems release its claim, then claim the next
    python -I tools/next_chunk.py --range 1578 1771     only hand out chunks in this range

A chunk is waiting when NNNN.tsv exists without NNNN.out.tsv / .imported / .inchat.
Claiming writes NNNN.inchat (the same marker `translate.py pick` uses).
If the finished chunk still has problems its claim is kept and nothing new is claimed (exit 1).
Prints NEXT=none when the queue is empty.

Orchestration used for the big passes: start ~10 agents, each with
"Follow docs/AGENT_CHUNK_TASK.md, your chunk is NNNN"; when one finishes, run
`next_chunk.py NNNN` and start a new agent on the printed chunk.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "work" / "queue"


def waiting(lo, hi):
    for p in sorted(Q.glob("*.tsv")):
        n = p.stem
        if not n.isdigit() or not lo <= int(n) <= hi:
            continue
        if any((Q / f"{n}{s}").exists() for s in (".out.tsv", ".imported", ".inchat")):
            continue
        yield n


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("done", nargs="?", help="chunk just finished: check it and release its claim")
    ap.add_argument("--range", nargs=2, type=int, default=(0, 99999), metavar=("FROM", "TO"))
    a = ap.parse_args()

    if a.done:
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "translate.py"), "check", a.done],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        last = (r.stdout.strip().splitlines() or [r.stderr.strip()])[-1]
        print(last)
        if " 0 problems" not in last:
            print(f"KEEP CLAIM {a.done} - fix the problems above first")
            sys.exit(1)
        (Q / f"{a.done}.inchat").unlink(missing_ok=True)

    nxt = next(waiting(*a.range), None)
    if nxt:
        (Q / f"{nxt}.inchat").write_text("claimed by next_chunk.py\n", encoding="utf-8")
    print(f"NEXT={nxt or 'none'}")


if __name__ == "__main__":
    main()
