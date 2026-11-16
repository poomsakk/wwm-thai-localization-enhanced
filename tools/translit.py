#!/usr/bin/env python3
"""
Mandarin (pinyin) -> Thai transliteration, rule based, so names come out the
same way every time. Loosely follows the Royal Institute (ราชบัณฑิตยสถาน)
convention, simplified for game text (no phinthu ฺ marks).

    python translit.py 开封 长安 赵州        -> ไคเฟิง ฉางอาน จ้าวโจว

Tone handling (Thai tone ≈ Mandarin tone):
  mid-class initial  (ก จ ต ป อ):   t1 -, t2 ๋, t3 ่, t4 ้
  aspirated pair (low/high, e.g. ค/ข): t1 low, t2 high, t3 high+่, t4 low+่
  sonorant (ม น ล ร ย ว):          t1 C, t2 หC, t3 หC+่, t4 C+่
Anything a rule gets wrong is fixed with a glossary override, not here.
"""
import re
import sys

from pypinyin import Style, pinyin

MID = {"b": "ป", "d": "ต", "g": "ก", "j": "จ", "zh": "จ", "z": "จ", "": "อ"}
PAIR = {"p": ("พ", "ผ"), "t": ("ท", "ถ"), "k": ("ค", "ข"), "q": ("ช", "ฉ"), "ch": ("ช", "ฉ"),
        "c": ("ช", "ฉ"), "f": ("ฟ", "ฝ"), "h": ("ฮ", "ห"), "x": ("ซ", "ส"), "s": ("ซ", "ส"),
        "sh": ("ซ", "ส")}
SON = {"m": "ม", "n": "น", "l": "ล", "r": "ร", "y": "ย", "w": "ว"}
MID_MARK = {1: "", 2: "๋", 3: "่", 4: "้"}

# C = initial consonant(s), T = tone mark (placed after any above/below vowel)
FINALS = {
    "a": "CTา", "ai": "ไCT", "ao": "เCTา", "an": "CTาน", "ang": "CTาง",
    "o": "CTอ", "ou": "โCTว", "ong": "CTง",
    "e": "เCTอ", "ei": "เCTย", "en": "เCิTน", "eng": "เCิTง", "er": "เอTอร์",
    "i": "CีT", "ia": "เCีTย", "iao": "เCีTยว", "ian": "เCีTยน", "iang": "เCีTยง",
    "ie": "เCีTย", "in": "CิTน", "ing": "CิTง", "iong": "CยTง", "iu": "CิTว",
    "u": "CูT", "ua": "CวTา", "uo": "CัTว", "uai": "ไCวT", "ui": "CุTย",
    "uan": "CTวน", "uang": "CวTาง", "un": "CุTน",
    # ü family (after j q x l n, or y-)
    "v": "CวีT", "ve": "เCวีTย", "van": "เCวีTยน", "vn": "CวิTน",
}
APICAL = "CืTอ"  # zhi chi shi ri zi ci si

INITIALS = ["zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h",
            "j", "q", "x", "r", "z", "c", "s", "y", "w"]


def split_syllable(s):
    """'zhuang4' -> ('zh', 'uang', 4). Uses pinyin with tone number, ü written as v."""
    tone = int(s[-1]) if s[-1].isdigit() else 5
    s = s.rstrip("012345").replace("ü", "v").replace("u:", "v")
    ini = next((i for i in INITIALS if s.startswith(i)), "")
    fin = s[len(ini):]
    # y / w spellings -> real finals
    if ini == "y":
        if fin in ("i", "in", "ing"):
            ini, fin = "", fin
        elif fin.startswith("u"):          # yu yue yuan yun = ü
            fin = "v" + fin[1:]
            fin = {"v": "v", "ve": "e_y", "van": "uan", "vn": "un"}.get(fin, fin)
            if fin == "v":
                ini = ""
        elif fin == "e":
            fin = "e_ye"
        elif fin == "an":
            fin = "ian"
    elif ini == "w":
        if fin == "u":
            ini = ""
    if ini in ("j", "q", "x") and fin.startswith("u"):
        fin = "v" + fin[1:]
    if ini in ("l", "n") and fin.startswith("v"):
        pass
    return ini, fin, tone


def consonant(ini, tone):
    """Return (initial cluster string, tone mark)."""
    t = 1 if tone == 5 else tone
    if ini in PAIR:
        low, high = PAIR[ini]
        return {1: (low, ""), 2: (high, ""), 3: (high, "่"), 4: (low, "่")}[t]
    if ini in SON:
        c = SON[ini]
        return {1: (c, ""), 2: ("ห" + c, ""), 3: ("ห" + c, "่"), 4: (c, "่")}[t]
    return MID.get(ini, "อ"), MID_MARK[t]


def syllable(s):
    ini, fin, tone = split_syllable(s)
    if fin == "e_ye":                     # ye -> เย่
        c, m = consonant("y", tone)
        return "เ" + c + m
    if fin == "e_y":                      # yue -> เยว่
        c, m = consonant("y", tone)
        return "เ" + c + "ว" + m
    if ini == "zh" and fin == "ao":       # 赵 -> จ้าว (common usage)
        c, m = consonant(ini, tone)
        return c + m + "าว"
    if fin == "i" and ini in ("zh", "ch", "sh", "r", "z", "c", "s"):
        tpl = APICAL
    elif ini == "h" and fin == "uang":    # 黄 -> หวง (common usage; keeps it apart from 王)
        tpl = "CวTง"
    elif ini == "w" and fin == "ang":     # 王 -> หวัง, 旺 -> วั่ง (common usage)
        tpl = "CัTง"
    else:
        tpl = FINALS.get(fin)
        if tpl is None:
            return s                      # unknown -> leave pinyin visible for review
    c, m = consonant(ini, tone)
    return tpl.replace("C", c).replace("T", m)


def translit(text, sep=""):
    """Transliterate Chinese text; non-Chinese characters pass through (· -> ·)."""
    out = []
    for ch, py in zip(text, pinyin(text, style=Style.TONE3, neutral_tone_with_five=True, errors=lambda x: [[c] for c in x])):
        p = py[0]
        out.append(syllable(p) if re.fullmatch(r"[a-zü:]+[1-5]", p) else p)
    return sep.join(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for w in sys.argv[1:]:
        print(w, translit(w))
