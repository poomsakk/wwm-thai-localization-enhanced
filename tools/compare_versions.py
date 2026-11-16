#!/usr/bin/env python3
"""
compare_versions — side-by-side HTML of two translations of the same chunks.

    python -I tools/compare_versions.py 1526 1527 1528
    -> work/compare/compare_1526-1528.html   (zh | in-chat .out.tsv | agent .agent.tsv)

Per item it shows the Chinese source, both Thai versions, their lengths and a
character similarity score (rows coloured by similarity).
"""
import difflib
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "work" / "queue"


def unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append({"n": "\n", "t": "\t", "\\": "\\", "r": "\r"}.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def read(path, col):
    d = {}
    if not path.exists():
        return d
    for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        p = line.split("\t")
        if len(p) > col:
            d[p[0]] = unesc(p[col])
    return d


def esc(s):
    return html.escape(s).replace("\n", "<br>")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    chunks = sys.argv[1:]
    rows, sims = [], []
    for c in chunks:
        zh = read(Q / f"{c}.tsv", 1)
        a = read(Q / f"{c}.out.tsv", 1)
        b = read(Q / f"{c}.agent.tsv", 1)
        for sid, src in zh.items():
            ta, tb = a.get(sid, ""), b.get(sid, "")
            same = src.startswith("@en:")
            r = difflib.SequenceMatcher(None, ta, tb).ratio() if ta and tb else 0.0
            if not same:
                sims.append(r)
            rows.append((c, sid, src, ta, tb, r, same))
    avg = sum(sims) / len(sims) if sims else 0
    body = []
    for c, sid, src, ta, tb, r, same in rows:
        cls = "same" if same else ("hi" if r >= .6 else "mid" if r >= .35 else "lo")
        body.append(
            f"<tr class='{cls}'><td class='id'>{c}<br>{sid}<br><b>{'—' if same else f'{r:.0%}'}</b><br>"
            f"<small>{len(ta)} / {len(tb)}</small></td><td class='zh'>{esc(src)}</td>"
            f"<td>{esc(ta)}</td><td>{esc(tb)}</td></tr>")
    page = f"""<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Compare chat vs agent</title>
<style>
:root{{--bg:#fff;--fg:#1b1b1b;--line:#ddd;--hi:#eef8ee;--mid:#fff8e6;--lo:#fdeeee;--muted:#666}}
@media (prefers-color-scheme:dark){{:root{{--bg:#161616;--fg:#e8e8e8;--line:#333;--hi:#17261a;--mid:#2a2414;--lo:#2c1818;--muted:#aaa}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,sans-serif;margin:16px}}
table{{border-collapse:collapse;width:100%;table-layout:fixed}}
th,td{{border:1px solid var(--line);padding:8px;vertical-align:top;word-wrap:break-word}}
th{{position:sticky;top:0;background:var(--bg)}} td.id{{width:80px;font-size:12px;color:var(--muted)}}
td.zh{{font-size:14px}} tr.hi td{{background:var(--hi)}} tr.mid td{{background:var(--mid)}} tr.lo td{{background:var(--lo)}}
.note{{color:var(--muted)}}
</style></head><body>
<h1>เทียบคำแปล: แชท vs Subagent — ก้อน {", ".join(chunks)}</h1>
<p class="note">ความเหมือนเฉลี่ย (ตัวอักษร, ไม่นับบรรทัด @en:) {avg:.0%} ·
เขียว ≥60% · เหลือง 35–60% · แดง &lt;35% (ต่างกันมาก ไม่ได้แปลว่าผิด) · ตัวเลขล่าง = ความยาวแชท / agent</p>
<table><tr><th style="width:80px">ก้อน/id</th><th>ต้นฉบับจีน</th><th>แปลในแชท (.out.tsv)</th><th>Subagent (.agent.tsv)</th></tr>
{''.join(body)}</table></body></html>"""
    out = ROOT / "work" / "compare" / f"compare_{chunks[0]}-{chunks[-1]}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"{len(rows)} items, avg similarity {avg:.0%} -> {out}")


if __name__ == "__main__":
    main()
