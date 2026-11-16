#!/usr/bin/env python3
"""
Translate chunk files with Z.ai (GLM) through its OpenAI-compatible API.

    set ZAI_API_KEY=your-key            (Command Prompt; never put the key in a file)
    python -I tools\\zai_translate.py 0117 0128          translate these chunks
    python -I tools\\zai_translate.py 0117 --dry-run     show the request size only, no API call
    python -I tools\\zai_translate.py 0117 --model glm-5.3-flash

Reads work/queue/NNNN.tsv, writes work/queue/NNNN.out.tsv (same format as the
Claude agents), then you run `translate.py check NNNN` and `build_mod.bat`.
Existing .out.tsv files are never overwritten unless --force is given.
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "work" / "queue"
BASE_URL = "https://api.z.ai/api/paas/v4/"
DEFAULT_MODEL = "glm-5.3"
BATCH = 100            # lines per request (keeps answers short enough to finish)
RETRIES = 2            # extra rounds for lines the model skipped

PROMPT = """You translate game text of "Where Winds Meet" (燕云十六声), a wuxia RPG set in 10th-century China, from Chinese into Thai.

INPUT: tab-separated lines: id, zh, en, th_old, terms
- zh = source, translate from this. en = official English, a hint only. th_old = old Thai, often wrong.
- terms = "中文=ไทย; ..." glossary entries found in the line. You MUST use these Thai renderings.
- "\\n" inside text means a line break. Keep it written as \\n.

OUTPUT: only lines "id<TAB>thai", one per input id, same ids. No header, no explanations, no code fences.

Follow the style guide and the translation guide below exactly (pronouns ข้า/เจ้า/ท่าน in speech, short modern UI Thai,
loanwords for game terms, Mandarin transliteration for names, keep #Y…#E codes / {0} / %s / | / \\n exactly, no Chinese left).
"""


def load_guides():
    parts = [PROMPT]
    for name in ("docs/STYLE_GUIDE.md", "docs/AGENT_TRANSLATION_GUIDE.md", "glossary/series_names.tsv"):
        p = ROOT / name
        if p.exists():
            parts.append(f"\n===== {name} =====\n" + p.read_text(encoding="utf-8"))
    return "\n".join(parts)


def read_chunk(name):
    lines = (Q / f"{name}.tsv").read_text(encoding="utf-8").splitlines()
    rows = {}
    for l in lines[1:]:
        if l.strip():
            rows[l.split("\t", 1)[0]] = l
    return rows


LINE_RE = re.compile(r"^\s*(\d+)\s*\t\s*(.*?)\s*$")
LOOSE_RE = re.compile(r"^\s*(\d+)[ 　]{1,4}(.*?)\s*$")   # model replaced the tab by spaces


def parse(text, wanted):
    out = {}
    for line in text.splitlines():
        if line.strip().startswith("```"):
            continue
        m = LINE_RE.match(line) or LOOSE_RE.match(line)
        if m and m.group(1) in wanted and m.group(2):
            out[m.group(1)] = m.group(2)
    return out


def translate_chunk(client, model, system, name, dry):
    rows = read_chunk(name)
    print(f"{name}: {len(rows)} lines")
    done = {}
    ids = list(rows)
    for attempt in range(RETRIES + 1):
        todo = [i for i in ids if i not in done]
        if not todo:
            break
        if attempt:
            print(f"  retry {attempt}: {len(todo)} missing lines")
        for b in range(0, len(todo), BATCH):
            part = todo[b:b + BATCH]
            user = "Translate all lines below:\n" + "\n".join(rows[i] for i in part)
            if dry:
                print(f"  [dry-run] request {b // BATCH + 1}: {len(part)} lines, "
                      f"system {len(system):,} chars, user {len(user):,} chars")
                continue
            for tries in range(4):
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                        temperature=0.3,
                    )
                    break
                except Exception as e:  # network / rate limit: wait and retry
                    wait = 10 * (tries + 1)
                    print(f"  request failed ({type(e).__name__}: {e}); retry in {wait}s")
                    time.sleep(wait)
            else:
                print("  giving up on this batch")
                continue
            got = parse(resp.choices[0].message.content or "", set(part))
            done.update(got)
            u = getattr(resp, "usage", None)
            print(f"  {len(got)}/{len(part)} lines" + (f"  (tokens in {u.prompt_tokens}, out {u.completion_tokens})" if u else ""))
        if dry:
            return
    out = Q / f"{name}.out.tsv"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("id\tth\n")
        for i in ids:
            if i in done:
                f.write(f"{i}\t{done[i]}\n")
    missing = len(ids) - len(done)
    print(f"  wrote {out.name}" + (f"  ({missing} lines still missing - re-run with --force or fix by hand)" if missing else ""))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("chunks", nargs="+")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite an existing .out.tsv")
    a = ap.parse_args()

    client = None
    if not a.dry_run:
        key = os.environ.get("ZAI_API_KEY")
        if not key:
            sys.exit("Set the ZAI_API_KEY environment variable first (see docs/EXTERNAL_AI_GUIDE.md).")
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url=BASE_URL)

    system = load_guides()
    for name in a.chunks:
        if not (Q / f"{name}.tsv").exists():
            print(f"{name}: no such chunk")
            continue
        if (Q / f"{name}.out.tsv").exists() and not a.force and not a.dry_run:
            print(f"{name}: {name}.out.tsv already exists - skipped (use --force to redo)")
            continue
        if (Q / f"{name}.imported").exists() and not a.force:
            print(f"{name}: already imported - skipped")
            continue
        translate_chunk(client, a.model, system, name, a.dry_run)


if __name__ == "__main__":
    main()
