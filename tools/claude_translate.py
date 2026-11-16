#!/usr/bin/env python3
"""
Translate chunk files with the Claude API (Anthropic SDK).

    set ANTHROPIC_API_KEY=sk-ant-...        (Command Prompt; never put the key in a file)

    python -I tools\\claude_translate.py run 0138 0139        translate now (results in seconds)
    python -I tools\\claude_translate.py run --next 5         the next 5 waiting chunks
    python -I tools\\claude_translate.py batch --next 50      Message Batches API: 50% price, results within ~1 h
    python -I tools\\claude_translate.py collect              download finished batches -> .out.tsv
    python -I tools\\claude_translate.py run 0138 --dry-run   show what would be sent, no API call

Reads work/queue/NNNN.tsv, writes work/queue/NNNN.out.tsv (same format as before);
then `translate.py check NNNN` and `build_mod.bat` work as usual.
Options: --model (default claude-opus-5-5), --effort low|medium|high (default low), --force.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "work" / "queue"
BATCH_LOG = Q / "claude_batches.json"
MODEL = "claude-opus-5-5"
MAX_TOKENS = 64000     # a 300-line chunk can answer with ~30k tokens
PRICE = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}

INSTRUCTIONS = """You translate game text of "Where Winds Meet" (燕云十六声), a wuxia RPG set in 10th-century China, from Chinese into Thai, for a fan localization mod.

The user message is a tab-separated chunk: id, zh, en, th_old, terms
- zh is the source: translate from it. en is the official English (a hint, often loose). th_old is the old official Thai (often wrong; reuse only when correct and in style).
- terms lists glossary entries found in the line ("中文=ไทย; ..."). Use these Thai renderings.
- Text is escaped: "\\n" means a line break. In your output use a real line break where the source has one.

Return one translation per input id. Follow the style guide, the translation guide and the fixed series names below exactly:
pronouns ข้า/เจ้า/ท่าน in character speech, short modern Thai for UI, loanwords for game terms, Mandarin transliteration for names,
and keep color codes (#Y…#E), placeholders ({0}, %s), the | male|female separator and the number of line breaks exactly. No Chinese characters may remain.
"""

SCHEMA = {
    "type": "object",
    "properties": {"translations": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "th": {"type": "string"}},
        "required": ["id", "th"], "additionalProperties": False}}},
    "required": ["translations"], "additionalProperties": False,
}


# ------------------------------------------------------------------ helpers
def system_blocks():
    parts = [INSTRUCTIONS]
    for name in ("docs/STYLE_GUIDE.md", "docs/AGENT_TRANSLATION_GUIDE.md", "glossary/series_names.tsv"):
        p = ROOT / name
        if p.exists():
            parts.append(f"\n===== {name} =====\n" + p.read_text(encoding="utf-8"))
    # stable text first + cache breakpoint: every request after the first reads it from cache
    return [{"type": "text", "text": "\n".join(parts), "cache_control": {"type": "ephemeral"}}]


def chunk_text(name):
    return (Q / f"{name}.tsv").read_text(encoding="utf-8")


def chunk_ids(name):
    return [l.split("\t", 1)[0] for l in chunk_text(name).splitlines()[1:] if l.strip()]


def params(name, model, effort):
    return dict(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system_blocks(),
        messages=[{"role": "user", "content": chunk_text(name)}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
    )


def esc(s):
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")


def write_out(name, text):
    """Parse the JSON answer and write NNNN.out.tsv. Returns (written, expected)."""
    want = chunk_ids(name)
    got = {str(t["id"]): t["th"] for t in json.loads(text)["translations"]}
    with open(Q / f"{name}.out.tsv", "w", encoding="utf-8", newline="\n") as f:
        f.write("id\tth\n")
        for i in want:
            if i in got:
                f.write(f"{i}\t{esc(got[i])}\n")
    return len(set(want) & set(got)), len(want)


def waiting(n):
    names = [p.stem for p in sorted(Q.glob("*.tsv")) if p.stem.isdigit()
             and not (Q / f"{p.stem}.out.tsv").exists() and not (Q / f"{p.stem}.imported").exists()
             and not (Q / f"{p.stem}.inchat").exists()]   # claimed by an in-chat /translate-next run
    queued = set()
    if BATCH_LOG.exists():
        for b in json.loads(BATCH_LOG.read_text(encoding="utf-8")):
            if not b.get("collected"):
                queued |= set(b["chunks"])
    return [x for x in names if x not in queued][:n]


def pick(a):
    names = list(a.chunks) + (waiting(a.next) if a.next else [])
    keep = []
    for n in names:
        if not (Q / f"{n}.tsv").exists():
            print(f"{n}: no such chunk")
        elif (Q / f"{n}.imported").exists():
            print(f"{n}: already imported - skipped")
        elif (Q / f"{n}.out.tsv").exists() and not a.force:
            print(f"{n}: {n}.out.tsv exists - skipped (--force to redo)")
        else:
            keep.append(n)
    return keep


def cost(model, u, batch=False):
    pin, pout = PRICE.get(model, (0, 0))
    c = (u["in"] * pin + u["cw"] * pin * 1.25 + u["cr"] * pin * 0.1 + u["out"] * pout) / 1e6
    return c / 2 if batch else c


def client():
    import anthropic
    return anthropic, anthropic.Anthropic()  # reads ANTHROPIC_API_KEY


# ------------------------------------------------------------------ commands
def cmd_run(a):
    names = pick(a)
    if a.dry_run:
        sys_len = len(system_blocks()[0]["text"])
        for n in names:
            print(f"[dry-run] {n}: {len(chunk_ids(n))} lines, system {sys_len:,} chars (cached), chunk {len(chunk_text(n)):,} chars")
        return
    anthropic, cl = client()
    usage = {"in": 0, "out": 0, "cw": 0, "cr": 0}
    for n in names:
        try:
            # streaming: long answers would otherwise hit the HTTP timeout
            with cl.beta.messages.stream(**params(n, a.model, a.effort),
                                         betas=["server-side-fallback-2026-07-01"], fallbacks="default") as s:
                r = s.get_final_message()
        except anthropic.AuthenticationError:
            sys.exit("API key rejected - check ANTHROPIC_API_KEY.")
        except anthropic.RateLimitError:
            print("rate limited - stopping; run again later to continue")
            break
        except anthropic.APIStatusError as e:
            print(f"{n}: API error {e.status_code} {e.message}")
            continue
        except anthropic.APIConnectionError:
            print(f"{n}: network error - skipped")
            continue
        if r.stop_reason != "end_turn":
            print(f"{n}: stopped ({r.stop_reason}) - no file written")
            continue
        text = next((b.text for b in r.content if b.type == "text"), "")
        ok, total = write_out(n, text)
        u = r.usage
        usage["in"] += u.input_tokens
        usage["out"] += u.output_tokens
        usage["cw"] += u.cache_creation_input_tokens or 0
        usage["cr"] += u.cache_read_input_tokens or 0
        print(f"{n}: {ok}/{total} lines -> {n}.out.tsv   (in {u.input_tokens}, cache read {u.cache_read_input_tokens or 0}, out {u.output_tokens})")
        time.sleep(0.5)
    print(f"total tokens {usage}  ≈ ${cost(a.model, usage):.2f}")


def cmd_batch(a):
    names = pick(a)
    if not names:
        print("nothing to submit")
        return
    if a.dry_run:
        print(f"[dry-run] would submit {len(names)} chunks: {names[0]} .. {names[-1]}")
        return
    anthropic, cl = client()
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    reqs = [Request(custom_id=n, params=MessageCreateParamsNonStreaming(**params(n, a.model, a.effort))) for n in names]
    b = cl.messages.batches.create(requests=reqs)
    log = json.loads(BATCH_LOG.read_text(encoding="utf-8")) if BATCH_LOG.exists() else []
    log.append({"id": b.id, "chunks": names, "model": a.model, "created": time.strftime("%Y-%m-%d %H:%M")})
    BATCH_LOG.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(f"submitted batch {b.id} with {len(names)} chunks ({names[0]} .. {names[-1]}).")
    print("Run `python -I tools\\claude_translate.py collect` later (usually within an hour).")


def cmd_collect(a):
    if not BATCH_LOG.exists():
        print("no batches submitted yet")
        return
    anthropic, cl = client()
    log = json.loads(BATCH_LOG.read_text(encoding="utf-8"))
    for entry in log:
        if entry.get("collected"):
            continue
        b = cl.messages.batches.retrieve(entry["id"])
        if b.processing_status != "ended":
            rc = b.request_counts
            print(f"{entry['id']}: still running (processing {rc.processing}, done {rc.succeeded})")
            continue
        usage = {"in": 0, "out": 0, "cw": 0, "cr": 0}
        failed = []
        for r in cl.messages.batches.results(entry["id"]):
            n = r.custom_id
            if r.result.type != "succeeded" or r.result.message.stop_reason != "end_turn":
                failed.append(n)
                continue
            m = r.result.message
            text = next((x.text for x in m.content if x.type == "text"), "")
            ok, total = write_out(n, text)
            usage["in"] += m.usage.input_tokens
            usage["out"] += m.usage.output_tokens
            usage["cw"] += m.usage.cache_creation_input_tokens or 0
            usage["cr"] += m.usage.cache_read_input_tokens or 0
            print(f"{n}: {ok}/{total} lines -> {n}.out.tsv")
        entry["collected"] = True
        print(f"{entry['id']}: done; failed chunks (resubmit later): {failed or 'none'};"
              f" ≈ ${cost(entry['model'], usage, batch=True):.2f}")
    BATCH_LOG.write_text(json.dumps(log, indent=1), encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("run", "batch"):
        s = sub.add_parser(name)
        s.add_argument("chunks", nargs="*")
        s.add_argument("--next", type=int, default=0, help="also take the next N waiting chunks")
        s.add_argument("--model", default=MODEL)
        s.add_argument("--effort", default="low", choices=["low", "medium", "high"])
        s.add_argument("--force", action="store_true")
        s.add_argument("--dry-run", action="store_true")
    sub.add_parser("collect")
    a = p.parse_args()
    {"run": cmd_run, "batch": cmd_batch, "collect": cmd_collect}[a.cmd](a)


if __name__ == "__main__":
    main()
