#!/usr/bin/env python3
"""
Phase 3 — translate source texts in work/wwm.db with Claude.

Commands
  sample  --n 60 [--out work/pilot]        stratified pilot sample -> prompt files (no API call)
  import  <result.json> [--tag NAME]        import {"translations":[{"id","th"}]} + validate
  run     [--limit N] [--category C]        translate via Messages API (sync, needs credentials)
  batch-submit [--limit N] [--category C]   submit via Message Batches API (50% price)
  batch-collect <batch_id>                  download + import batch results
  export-tsv <out.tsv>                      key -> th_new TSV for `wwmloc.py patch`
  report                                    progress per category

Options: --model (default claude-opus-5-5) --effort (low|medium|high, default low)
Credentials: ANTHROPIC_API_KEY env var (or an `ant auth login` profile).
"""
import argparse
import collections
import csv
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "work" / "wwm.db"
STYLE = ROOT / "docs" / "STYLE_GUIDE.md"
GLOSSARY = ROOT / "glossary" / "glossary.tsv"

MODEL = "claude-opus-5-5"
MAX_ITEMS = 60          # items per request
MAX_ZH_CHARS = 2500     # source chars per request
MAX_TOKENS = 16000

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
FOREIGN_RE = re.compile(r"[\u0400-\u04ff\u0600-\u06ff\u0900-\u0dff\u3040-\u30ff\uac00-\ud7af]")
TOKEN_RES = [re.compile(r"#[A-Za-z]"), re.compile(r"\{[^{}]*\}"),
             re.compile(r"%(?:\d+\$)?[-+ 0#]*\d*(?:\.\d+)?[sdif]")]

SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "th": {"type": "string"}},
                "required": ["id", "th"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You translate the Chinese game text of Where Winds Meet (燕云十六声), a wuxia open-world RPG set in 10th-century China, into Thai.

Each request is a JSON list of items: id, zh (the source — translate from this), en (official English, a hint for context only; it is often loose), th_old (the old official Thai — frequently wrong or inconsistent; keep it only where it is already correct and fits the style guide), cat (ui_short | label | description | dialogue | long_text), and terms (glossary entries that appear in this item — you MUST use these Thai renderings).

Rules:
- Follow the style guide below exactly (pronouns ข้า/เจ้า/ท่าน in dialogue, modern sentence structure, loanwords only in system/combat/UI context, Mandarin transliteration for names).
- Preserve every technical token exactly and in a sensible position: #Y…#E style color codes, {0}/{name} placeholders, %s/%d, line breaks (\\n count must match), and the | male|female separator (translate both sides).
- Never leave Chinese characters in the output. Unknown proper names: transliterate from Mandarin.
- ui_short / label: short and natural, no trailing period.
- Return one translation per input id, nothing else.

=== STYLE GUIDE ===
"""


# ---------------------------------------------------------------- data access
def db():
    con = sqlite3.connect(DB)
    cols = {r[1] for r in con.execute("PRAGMA table_info(sources)")}
    for col in ("model", "updated_at"):
        if col not in cols:
            con.execute(f"ALTER TABLE sources ADD COLUMN {col} TEXT")
    return con


def load_glossary():
    with open(GLOSSARY, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    # pronoun / address entries are context-dependent (小人 = "ข้าน้อย" or "คนถ่อย");
    # the style guide covers them, so they are not forced as per-item terms
    return {r["zh"]: r["th"] for r in rows if r["th"] and r["type"] not in ("pronoun", "address")}


def terms_for(zh, gloss, maxlen):
    found = {}
    for i in range(len(zh)):
        for L in range(min(maxlen, len(zh) - i), 1, -1):
            s = zh[i:i + L]
            if s in gloss:
                found[s] = gloss[s]
                break  # longest match at this position
    return found


def system_prompt():
    return INSTRUCTIONS + STYLE.read_text(encoding="utf-8")


def make_items(rows, gloss):
    maxlen = max(map(len, gloss)) if gloss else 1
    items = []
    for sid, zh, en, th_old, cat in rows:
        it = {"id": sid, "zh": zh, "en": en or "", "th_old": th_old or "", "cat": cat}
        t = terms_for(zh, gloss, maxlen)
        if t:
            it["terms"] = t
        items.append(it)
    return items


def chunk(items):
    batch, chars = [], 0
    for it in items:
        if batch and (len(batch) >= MAX_ITEMS or chars + len(it["zh"]) > MAX_ZH_CHARS):
            yield batch
            batch, chars = [], 0
        batch.append(it)
        chars += len(it["zh"])
    if batch:
        yield batch


def select(con, limit=None, category=None, status=("todo",), new_only=False):
    q = ("SELECT src_id, zh, en, th_old, category FROM sources WHERE status IN (%s) AND category != 'empty'"
         % ",".join("?" * len(status)))
    args = list(status)
    if new_only:  # texts added by tools/update_game.py (note new:<version>)
        q += " AND note LIKE 'new:%'"
    if category:
        q += " AND category = ?"
        args.append(category)
    q += " ORDER BY priority, n_keys DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    return con.execute(q, args).fetchall()


# ---------------------------------------------------------------- validation
def tokens(s):
    return sorted(t for r in TOKEN_RES for t in r.findall(s))


def validate(zh, th):
    errs = []
    if zh.strip() and not th.strip():
        errs.append("empty")
    # {placeholder} names may legitimately be Chinese (e.g. {数量1}); ignore them
    if CJK_RE.search(TOKEN_RES[1].sub("", th)):
        errs.append("chinese_left")
    if FOREIGN_RE.search(th):
        errs.append("foreign_script")  # e.g. a stray Devanagari/Kana/Hangul letter
    if tokens(zh) != tokens(th):
        errs.append(f"tokens {tokens(zh)} != {tokens(th)}")
    # printf-style %s/%d are filled in order: their sequence must not change
    pf_zh, pf_th = TOKEN_RES[2].findall(zh), TOKEN_RES[2].findall(th)
    if sorted(pf_zh) == sorted(pf_th) and pf_zh != pf_th and not any("$" in t for t in pf_zh):
        errs.append(f"printf_order {pf_zh} -> {pf_th}")
    if zh.count("\n") != th.count("\n"):
        errs.append("newline_count")
    if zh.count("|") != th.count("|"):
        errs.append("gender_split")
    return errs


def store(con, results, tag):
    src = dict(con.execute(
        "SELECT src_id, zh FROM sources WHERE src_id IN (%s)" % ",".join("?" * len(results)),
        list(results)).fetchall()) if results else {}
    ok = bad = 0
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for sid, th in results.items():
        if sid not in src:
            continue
        errs = validate(src[sid], th)
        status = "done" if not errs else "needs_fix"
        ok += not errs
        bad += bool(errs)
        con.execute("UPDATE sources SET th_new=?, status=?, note=?, model=?, updated_at=? WHERE src_id=?",
                    (th, status, "; ".join(errs) or None, tag, now, sid))
    con.commit()
    return ok, bad


def parse_result(text):
    data = json.loads(text)
    return {int(t["id"]): t["th"] for t in data["translations"]}


# ---------------------------------------------------------------- API
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


def request_params(batch, model, effort):
    return dict(
        model=model,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": json.dumps(batch, ensure_ascii=False)}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": SCHEMA}},
    )


def cmd_run(a):
    import anthropic
    client = anthropic.Anthropic()
    con = db()
    items = make_items(select(con, a.limit, a.category), load_glossary())
    usage = collections.Counter()
    for n, batch in enumerate(chunk(items), 1):
        try:
            resp = client.beta.messages.create(
                **request_params(batch, a.model, a.effort),
                betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        except anthropic.RateLimitError:
            print("rate limited; stopping — re-run to continue")
            break
        except anthropic.APIStatusError as e:
            print(f"request {n} failed: {e.status_code} {e.message}")
            continue
        if resp.stop_reason in ("refusal", "max_tokens"):
            print(f"request {n}: stop_reason={resp.stop_reason}; items left as todo")
            continue
        text = next((b.text for b in resp.content if b.type == "text"), "")
        ok, bad = store(con, parse_result(text), resp.model)
        u = resp.usage
        usage.update(inp=u.input_tokens, out=u.output_tokens,
                     cw=u.cache_creation_input_tokens or 0, cr=u.cache_read_input_tokens or 0)
        print(f"request {n}: {len(batch)} items, ok {ok}, needs_fix {bad}, in {u.input_tokens} out {u.output_tokens}")
    pin, pout = PRICES.get(a.model, (0, 0))
    cost = (usage["inp"] * pin + usage["cw"] * pin * 1.25 + usage["cr"] * pin * 0.1 + usage["out"] * pout) / 1e6
    print(f"usage {dict(usage)}  ≈ ${cost:.2f} (standard price)")


def cmd_batch_submit(a):
    import anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    client = anthropic.Anthropic()
    con = db()
    items = make_items(select(con, a.limit, a.category), load_glossary())
    reqs = [Request(custom_id=f"b{n}", params=MessageCreateParamsNonStreaming(**request_params(b, a.model, a.effort)))
            for n, b in enumerate(chunk(items))]
    for i in range(0, len(reqs), 10000):
        batch = client.messages.batches.create(requests=reqs[i:i + 10000])
        print(f"submitted {batch.id} ({len(reqs[i:i + 10000])} requests)")
    con.executemany("UPDATE sources SET status='queued' WHERE src_id=?", [(it["id"],) for it in items])
    con.commit()


def cmd_batch_collect(a):
    import anthropic
    client = anthropic.Anthropic()
    con = db()
    b = client.messages.batches.retrieve(a.batch_id)
    if b.processing_status != "ended":
        print(f"status {b.processing_status}: {b.request_counts}")
        return
    ok = bad = failed = 0
    for r in client.messages.batches.results(a.batch_id):
        if r.result.type != "succeeded" or r.result.message.stop_reason != "end_turn":
            failed += 1
            continue
        text = next((x.text for x in r.result.message.content if x.type == "text"), "")
        o, f = store(con, parse_result(text), r.result.message.model)
        ok, bad = ok + o, bad + f
    con.execute("UPDATE sources SET status='todo' WHERE status='queued'")  # failed requests go back to the queue
    con.commit()
    print(f"ok {ok}, needs_fix {bad}, failed requests {failed}")


# ---------------------------------------------------------------- offline helpers
def cmd_sample(a):
    con = db()
    per = max(1, a.n // 5)
    rows = []
    for cat in ("ui_short", "label", "description", "dialogue", "long_text"):
        rows += con.execute(
            "SELECT src_id, zh, en, th_old, category FROM sources WHERE category=? AND status='todo' "
            "AND zh_len >= 2 ORDER BY (n_keys > 20) DESC, abs(random()) % 1000 LIMIT ?",
            (cat, per if cat != "long_text" else max(1, per // 4))).fetchall()
    items = make_items(rows, load_glossary())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "system.md").write_text(system_prompt(), encoding="utf-8")
    (out / "items.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} items -> {out}/items.json (+ system.md)")


def cmd_import(a):
    con = db()
    ok, bad = store(con, parse_result(Path(a.file).read_text(encoding="utf-8")), a.tag)
    print(f"imported ok {ok}, needs_fix {bad}")
    for sid, zh, th, note in con.execute(
            "SELECT src_id, zh, th_new, note FROM sources WHERE status='needs_fix' AND model=?", (a.tag,)):
        print(f"  needs_fix {sid}: {note} | {zh[:40]} -> {th[:40]}")


def tsv_esc(s):
    return (s or "").replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def tsv_unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append({"\\": "\\", "t": "\t", "n": "\n", "r": "\r"}.get(s[i + 1], "\\" + s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


SYSTEM_DESC_RE = re.compile(
    r"#[A-Za-z]|\d|%|伤害|效果|获得|使用|提升|降低|消耗|冷却|调息|触发|属性|解锁|奖励|领取|完成|击败|"
    r"秒|层|次数|上限|装备|道具|技能|状态|增加|减少|恢复|回复|兑换|购买|活动|任务|点击|开启|可在|前往")


def select_ui_system(con, limit):
    """UI + labels + system-like descriptions (skills, items, effects), most-used first; no dialogue."""
    rows = con.execute(
        "SELECT src_id, zh, en, th_old, category, n_keys FROM sources WHERE status='todo' "
        "AND category IN ('ui_short','label','description') ORDER BY n_keys DESC").fetchall()
    out = [r[:5] for r in rows if r[4] != "description" or SYSTEM_DESC_RE.search(r[1])]
    return out[:limit] if limit else out


def cmd_chunks(a):
    """Write todo items to work/queue/NNNN.tsv for in-chat (subscription) translation."""
    con = db()
    rows = select_ui_system(con, a.limit) if a.ui_system else select(con, a.limit, a.category, new_only=a.new)
    items = make_items(rows, load_glossary())
    qdir = ROOT / "work" / "queue"
    qdir.mkdir(parents=True, exist_ok=True)
    start = max([int(p.stem) for p in qdir.glob("[0-9]*.tsv") if p.stem.isdigit()] + [0]) + 1
    n = 0
    for i in range(0, len(items), a.size):
        part = items[i:i + a.size]
        name = f"{start + n:04d}"
        with open(qdir / f"{name}.tsv", "w", encoding="utf-8", newline="\n") as f:
            f.write("id\tzh\ten\tth_old\tterms\n")
            for it in part:
                terms = "; ".join(f"{k}={v}" for k, v in it.get("terms", {}).items())
                f.write("\t".join([str(it["id"]), tsv_esc(it["zh"]), tsv_esc(it["en"]), tsv_esc(it["th_old"]), terms]) + "\n")
        con.executemany("UPDATE sources SET status='queued', note=? WHERE src_id=?", [(f"chunk:{name}", it["id"]) for it in part])
        n += 1
    con.commit()
    print(f"{len(items)} items -> {n} chunk files in {qdir} (from {start:04d})")


def cmd_rechunk(a):
    """Re-cut all waiting chunk files (no .out.tsv, not imported, not in a Claude batch) to a new size."""
    con = db()
    qdir = ROOT / "work" / "queue"
    in_batch = set()
    if (qdir / "claude_batches.json").exists():
        for b in json.loads((qdir / "claude_batches.json").read_text(encoding="utf-8")):
            if not b.get("collected"):
                in_batch |= set(b["chunks"])
    waiting = [p for p in sorted(qdir.glob("*.tsv")) if p.stem.isdigit() and p.stem not in in_batch
               and not (qdir / f"{p.stem}.out.tsv").exists() and not (qdir / f"{p.stem}.imported").exists()]
    if not waiting:
        print("no waiting chunks")
        return
    nxt = max([int(p.stem) for p in qdir.glob("*.tsv") if p.stem.isdigit()] + [0]) + 1
    old_dir = qdir / "split_originals"
    old_dir.mkdir(exist_ok=True)
    header, body = None, []
    for p in waiting:  # pool every waiting line in queue order, then cut to the new size
        lines = p.read_text(encoding="utf-8").splitlines()
        header = header or lines[0]
        body += [l for l in lines[1:] if l.strip()]
        p.rename(old_dir / p.name)
    made = []
    for i in range(0, len(body), a.size):
        name = f"{nxt:04d}"
        part = body[i:i + a.size]
        (qdir / f"{name}.tsv").write_text("\n".join([header] + part) + "\n", encoding="utf-8")
        con.executemany("UPDATE sources SET note=? WHERE src_id=?",
                        [(f"chunk:{name}", int(l.split("\t", 1)[0])) for l in part])
        made.append(name)
        nxt += 1
    con.commit()
    print(f"re-cut {len(waiting)} waiting chunk files ({len(body)} lines) into {len(made)} files of up to {a.size} lines"
          + f": {made[0]} .. {made[-1]}")


def cmd_import_tsv(a):
    """Import 'id<TAB>th' lines (escaped like the chunk files)."""
    con = db()
    res = {}
    for line in Path(a.file).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("id\t"):
            continue
        sid, _, th = line.partition("\t")
        res[int(sid)] = tsv_unesc(th)
    ok, bad = store(con, res, a.tag)
    print(f"{Path(a.file).name}: ok {ok}, needs_fix {bad}")
    for sid, zh, th, note in con.execute(
            "SELECT src_id, zh, th_new, note FROM sources WHERE status='needs_fix' AND src_id IN (%s)"
            % ",".join(map(str, res)) if res else "SELECT 1,2,3,4 WHERE 0"):
        print(f"  needs_fix {sid}: {note} | {zh[:40]} -> {th[:40]}")


def cmd_import_queue(a):
    """Import every work/queue/NNNN.out.tsv not imported yet (marked with NNNN.imported)."""
    qdir = ROOT / "work" / "queue"
    con = db()
    tot_ok = tot_bad = 0
    missing = []
    for out in sorted(qdir.glob("*.out.tsv")):
        name = out.name.split(".")[0]
        mark = qdir / f"{name}.imported"
        if mark.exists() or (a.only and name not in a.only):
            continue
        src_ids = {int(l.split("\t", 1)[0]) for l in (qdir / f"{name}.tsv").read_text(encoding="utf-8").splitlines()[1:] if l}
        res = {}
        for line in out.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("id\t"):
                continue
            sid, _, th = line.partition("\t")
            if sid.strip().isdigit():
                res[int(sid)] = tsv_unesc(th)
        ok, bad = store(con, {k: v for k, v in res.items() if k in src_ids}, f"chat-{name}")
        lost = src_ids - set(res)
        if lost:
            missing.append((name, len(lost)))
        tot_ok, tot_bad = tot_ok + ok, tot_bad + bad
        mark.write_text(f"ok {ok} needs_fix {bad} missing {len(lost)}\n", encoding="utf-8")
        print(f"{name}: ok {ok}, needs_fix {bad}, missing {len(lost)}")
    print(f"total ok {tot_ok}, needs_fix {tot_bad}; chunks with missing ids: {missing or 'none'}")


def cmd_check(a):
    """Dry-run check of NNNN.out.tsv files (any AI) without importing anything."""
    qdir = ROOT / "work" / "queue"
    for name in a.chunks:
        src, out = qdir / f"{name}.tsv", qdir / f"{name}{getattr(a, 'suffix', '.out')}.tsv"
        if not out.exists():
            print(f"{name}: no {out.name}")
            continue
        zh = {}
        for l in src.read_text(encoding="utf-8").splitlines()[1:]:
            p = l.split("\t")
            if len(p) > 1:
                zh[p[0]] = tsv_unesc(p[1])
        got, problems = {}, []
        for i, l in enumerate(out.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not l.strip() or l.startswith("id\t"):
                continue
            sid, sep, th = l.partition("\t")
            if not sep or not sid.strip().isdigit():
                problems.append(f"line {i}: not 'id<TAB>text': {l[:50]}")
                continue
            got[sid.strip()] = tsv_unesc(th)
        for sid in zh.keys() - got.keys():
            problems.append(f"id {sid}: missing")
        for sid in got.keys() - zh.keys():
            problems.append(f"id {sid}: not in this chunk")
        for sid, th in got.items():
            if sid in zh:
                errs = validate(zh[sid], th)
                if errs:
                    problems.append(f"id {sid}: {'; '.join(errs)} | {th[:40]}")
        print(f"{name}: {len(got)}/{len(zh)} lines, {len(problems)} problems")
        for p in problems[:30]:
            print("   ", p)


def cmd_review_csv(a):
    """Excel-friendly old-vs-new table: imported translations + finished-but-not-imported chunks."""
    con = db()
    qdir = ROOT / "work" / "queue"
    rows = {}
    for sid, cat, n, zh, en, old, new in con.execute(
            "SELECT src_id, category, n_keys, zh, en, th_old, th_new FROM sources WHERE status IN ('done','needs_fix')"):
        rows[sid] = [cat, n, zh, en, old, new, "imported", ""]
    meta = {r[0]: r[1:] for r in con.execute("SELECT src_id, category, n_keys, zh, en, th_old FROM sources")}
    for out in sorted(qdir.glob("*.out.tsv")):
        name = out.name.split(".")[0]
        if (qdir / f"{name}.imported").exists() or (a.chunks and name not in a.chunks):
            continue
        for l in out.read_text(encoding="utf-8-sig").splitlines():
            sid, sep, th = l.partition("\t")
            if sep and sid.strip().isdigit() and int(sid) in meta:
                cat, n, zh, en, old = meta[int(sid)]
                th = tsv_unesc(th)
                rows[int(sid)] = [cat, n, zh, en, old, th, f"chunk {name} (not built)", "; ".join(validate(zh, th))]
    if a.chunks:
        rows = {k: v for k, v in rows.items() if v[6].startswith("chunk")}
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "หมวด", "ใช้ในเกม(จุด)", "จีน", "อังกฤษ", "ไทยเดิม", "ไทยใหม่", "เปลี่ยน?", "ที่มา", "ปัญหาที่ตรวจเจอ"])
        for sid, (cat, n, zh, en, old, new, src, prob) in sorted(rows.items(), key=lambda kv: -kv[1][1]):
            w.writerow([sid, cat, n, zh, en, old, new, "" if old == new else "เปลี่ยน", src, prob])
    print(f"{len(rows)} rows -> {a.out}")


def cmd_pick(a):
    """Print one waiting chunk name for in-chat translation.
    Takes from the END of the queue so it never collides with `claude_translate.py batch --next N`
    (which takes from the front). Prints nothing if the queue is empty."""
    qdir = ROOT / "work" / "queue"
    in_batch = set()
    if (qdir / "claude_batches.json").exists():
        for b in json.loads((qdir / "claude_batches.json").read_text(encoding="utf-8")):
            if not b.get("collected"):
                in_batch |= set(b["chunks"])
    waiting = [p.stem for p in sorted(qdir.glob("*.tsv")) if p.stem.isdigit() and p.stem not in in_batch
               and not (qdir / f"{p.stem}.out.tsv").exists() and not (qdir / f"{p.stem}.imported").exists()
               and not (qdir / f"{p.stem}.inchat").exists()]
    if waiting:
        name = waiting[-1]
        (qdir / f"{name}.inchat").write_text("claimed for in-chat translation\n", encoding="utf-8")
        print(name)


def cmd_queue_status(a):
    """List chunk files: translated-and-imported vs waiting for translation."""
    qdir = ROOT / "work" / "queue"
    chunks = sorted(p.stem for p in qdir.glob("*.tsv") if p.stem.isdigit())
    imported = [c for c in chunks if (qdir / f"{c}.imported").exists()]
    ready = [c for c in chunks if c not in imported and (qdir / f"{c}.out.tsv").exists()]
    waiting = [c for c in chunks if c not in imported and c not in ready]
    print(f"imported: {len(imported)}   translated, not imported yet: {len(ready)} {ready[:10]}")
    print(f"waiting for translation: {len(waiting)}" + (f"  (next: {', '.join(waiting[:5])})" if waiting else ""))


def cmd_export(a):
    con = db()
    n = 0
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("key\ttext\n")
        for key, th in con.execute(
                "SELECT e.key, s.th_new FROM entries e JOIN sources s USING(src_id) WHERE s.status='done'"):
            f.write(key + "\t" + th.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r") + "\n")
            n += 1
    print(f"exported {n} keys -> {a.out}")


def cmd_report(a):
    con = db()
    print(f"{'category':12} {'todo':>8} {'done':>8} {'fix':>6} {'queued':>7}")
    for cat, todo, done, fix, q in con.execute(
            "SELECT category, sum(status='todo'), sum(status='done'), sum(status='needs_fix'), sum(status='queued') "
            "FROM sources GROUP BY 1 ORDER BY min(priority)"):
        print(f"{cat:12} {todo:8} {done:8} {fix:6} {q:7}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=MODEL)
    p.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--n", type=int, default=60); s.add_argument("--out", default=str(ROOT / "work/pilot"))
    s = sub.add_parser("import"); s.add_argument("file"); s.add_argument("--tag", default="manual")
    for name in ("run", "batch-submit"):
        s = sub.add_parser(name); s.add_argument("--limit", type=int); s.add_argument("--category")
    s = sub.add_parser("batch-collect"); s.add_argument("batch_id")
    s = sub.add_parser("chunks"); s.add_argument("--limit", type=int); s.add_argument("--category"); s.add_argument("--size", type=int, default=300)
    s.add_argument("--ui-system", action="store_true", help="UI/labels/system descriptions by usage, no dialogue")
    s.add_argument("--new", action="store_true", help="only texts added by the last game update (note new:...)")
    s = sub.add_parser("rechunk"); s.add_argument("--size", type=int, default=300)
    sub.add_parser("pick")
    s = sub.add_parser("import-tsv"); s.add_argument("file"); s.add_argument("--tag", default="chat")
    s = sub.add_parser("import-queue"); s.add_argument("only", nargs="*", help="chunk names (default: all finished)")
    sub.add_parser("queue-status")
    s = sub.add_parser("check"); s.add_argument("chunks", nargs="+", help="chunk names, e.g. 0117 0128"); s.add_argument("--suffix", default=".out", help="check NNNN<suffix>.tsv, e.g. .agent")
    s = sub.add_parser("review-csv"); s.add_argument("--out", default=str(ROOT / "compare_old_vs_new.csv"))
    s.add_argument("chunks", nargs="*", help="only these not-yet-built chunks (default: everything)")
    s = sub.add_parser("export-tsv"); s.add_argument("out")
    sub.add_parser("report")
    a = p.parse_args()
    {"sample": cmd_sample, "import": cmd_import, "run": cmd_run, "batch-submit": cmd_batch_submit,
     "batch-collect": cmd_batch_collect, "export-tsv": cmd_export, "report": cmd_report,
     "chunks": cmd_chunks, "import-tsv": cmd_import_tsv, "import-queue": cmd_import_queue,
     "queue-status": cmd_queue_status, "check": cmd_check, "review-csv": cmd_review_csv,
     "rechunk": cmd_rechunk, "pick": cmd_pick}[a.cmd](a)


if __name__ == "__main__":
    main()
