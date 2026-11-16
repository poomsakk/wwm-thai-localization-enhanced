#!/usr/bin/env python3
"""Project progress at a glance (read-only, no AI, no changes)."""
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "work" / "queue"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

_GAME = config.game_dir(required=False)
GAME_FILE = (_GAME / config.LOCALE_REL / "translate_words_map_th") if _GAME else Path("<game not found>")


def kind(cat, zh):
    if cat == "dialogue":
        return "บทสนทนา"
    if cat == "long_text":
        return "เนื้อเรื่องยาว / หนังสือ"
    if cat in ("description", "label") and re.search(r"伤害|技|秒|冷却|调息|层|触发|命中|暴击|会心|气血|攻击|防御|增益|减益|效果", zh):
        return "สกิล / การต่อสู้"
    if re.search(r"前往|击败|对话|完成|收集|寻找|调查|交给|护送|到达|帮助|任务|委托|探索", zh):
        return "ภารกิจ / เป้าหมาย"
    if cat == "description" and re.search(r"使用|获得|可用于|道具|材料|装备|外观|兑换|购买|礼包|开启后|食用", zh):
        return "คำอธิบายไอเทม"
    if cat == "description":
        return "คำอธิบายทั่วไป / NPC"
    return "UI / ปุ่ม / ชื่อ"


def bar(p, w=20):
    n = round(p * w)
    return "█" * n + "░" * (w - n)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(ROOT / "work" / "wwm.db")

    # translated but not yet built (finished .out.tsv without .imported marker)
    pending = set()
    chunks = sorted(p.stem for p in Q.glob("*.tsv") if p.stem.isdigit())
    imported = [c for c in chunks if (Q / f"{c}.imported").exists()]
    ready = [c for c in chunks if c not in imported and (Q / f"{c}.out.tsv").exists()]
    for c in ready:
        for l in (Q / f"{c}.out.tsv").read_text(encoding="utf-8-sig").splitlines()[1:]:
            sid = l.split("\t", 1)[0].strip()
            if sid.isdigit():
                pending.add(int(sid))
    in_batch = set()
    if (Q / "claude_batches.json").exists():
        for b in json.loads((Q / "claude_batches.json").read_text(encoding="utf-8")):
            if not b.get("collected"):
                in_batch |= set(b["chunks"])
    waiting = [c for c in chunks if c not in imported and c not in ready and c not in in_batch]

    agg = collections.defaultdict(lambda: [0, 0, 0, 0])  # keys, keys_in_game, keys_after_build, sources
    tot = [0, 0, 0, 0, 0]  # sources, keys, in_game_keys, after_build_keys, after_build_sources
    for sid, cat, zh, n, st in con.execute("SELECT src_id, category, zh, n_keys, status FROM sources WHERE category != 'empty'"):
        a = agg[kind(cat, zh)]
        a[0] += n
        tot[0] += 1
        tot[1] += n
        if st == "done":
            a[1] += n
            tot[2] += n
        if st == "done" or sid in pending:
            a[2] += n
            tot[3] += n
            tot[4] += 1
    needs_fix = con.execute("SELECT count(*) FROM sources WHERE status='needs_fix'").fetchone()[0]

    print("=" * 64)
    print(" WWM Thai Localization — ความคืบหน้า")
    print("=" * 64)
    print(f" ข้อความที่ผู้เล่นเห็น (ในเกมตอนนี้) {bar(tot[2]/tot[1])} {tot[2]/tot[1]:6.1%}")
    if tot[3] != tot[2]:
        print(f" หลังรัน build_mod.bat             {bar(tot[3]/tot[1])} {tot[3]/tot[1]:6.1%}")
    print(f" ต้นฉบับไม่ซ้ำที่แปลแล้ว             {tot[4]:,} / {tot[0]:,} ({tot[4]/tot[0]:.1%})")
    print()
    print(f" {'ประเภท':26} {'สัดส่วนในเกม':>12}   แปลแล้ว")
    for k, (keys, done, after, _) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
        print(f" {k:26} {keys/tot[1]:11.1%}   {bar(after/keys, 12)} {after/keys:6.1%}")
    print()
    print(" คิวงาน")
    print(f"   นำเข้าแล้ว                 {len(imported):5} ก้อน")
    print(f"   แปลเสร็จ รอ build_mod.bat   {len(ready):5} ก้อน" + (f"  ({', '.join(ready[:5])}{' ...' if len(ready) > 5 else ''})" if ready else ""))
    if in_batch:
        print(f"   อยู่ใน Claude batch         {len(in_batch):5} ก้อน  -> รัน claude_translate.py collect")
    print(f"   รอแปล                     {len(waiting):5} ก้อน" + (f"  (ถัดไป: {', '.join(waiting[:5])})" if waiting else ""))
    if needs_fix:
        print(f"   บรรทัดที่ไม่ผ่านการตรวจ      {needs_fix:5}  (ยังใช้ภาษาไทยเดิมในเกม)")
    print()
    build = ROOT / "work" / "build" / "translate_words_map_th"
    orig = ROOT / "backup" / "original" / "Package" / "translate_words_map_th"
    if GAME_FILE.exists():
        size = GAME_FILE.stat().st_size
        state = ("MOD (บิลด์ล่าสุด)" if build.exists() and size == build.stat().st_size else
                 "ORIGINAL (ภาษาไทยทางการ)" if orig.exists() and size == orig.stat().st_size else
                 "ไม่ตรงกับทั้งสองแบบ (เกมอัปเดต? รัน build_mod.bat ใหม่)")
        print(f" ไฟล์ภาษาไทยในเกม: {state}")
    print("=" * 64)


if __name__ == "__main__":
    main()
