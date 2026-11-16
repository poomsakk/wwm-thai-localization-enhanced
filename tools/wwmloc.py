#!/usr/bin/env python3
"""
wwmloc — read / write Where Winds Meet `translate_words_map_*` locale files.

Container layout (little-endian):
    u32 magic 0xDEADBEEF | u32 version (1) | u32 n_blocks
    u32 offsets[n_blocks + 1]            (relative to data start)
    data: per block -> u8 type (4 = zstd) | u32 comp_size | u32 raw_size | payload

Text block layout (decompressed), an open-addressing hash table:
    u64 capacity | u64 used | u32 TEXT_SIG | u32 ?
    u8  ctrl[capacity + 16]              (high bit set = empty slot), pad to 8
    slot[capacity] { u8 key[8] | u32 rel_off (from &rel_off) | u32 byte_len }
    utf-8 strings
Blocks whose signature differs (e.g. block 0, an index) are kept verbatim.

We never add/remove keys, so the hash table (ctrl + key order) is reused as is;
only the string region and each slot's offset/length are rewritten.

Usage:
    python wwmloc.py export <locale_file> <out.tsv>
    python wwmloc.py patch  <locale_file> <translations.tsv> <out_file>
    python wwmloc.py verify <locale_file>
TSV: header "key\ttext", key = 16 hex chars, text escaped (\\ \t \n \r).
"""
import struct
import sys

import zstandard

MAGIC = 0xDEADBEEF
TEXT_SIG = 0x595896DC  # bytes dc 96 58 59
ZSTD_LEVEL = 9


# ---------------------------------------------------------------- container
def read_container(path):
    data = open(path, "rb").read()
    magic, version, n = struct.unpack_from("<III", data, 0)
    if magic != MAGIC:
        raise ValueError(f"{path}: bad magic {magic:#x}")
    if n == 0:
        raise ValueError(f"{path}: single-block files are not supported yet")
    offs = struct.unpack_from(f"<{n + 1}I", data, 12)
    base = 12 + 4 * (n + 1)
    dz = zstandard.ZstdDecompressor()
    blocks = []
    for i in range(n):
        raw = data[base + offs[i]: base + offs[i + 1]]
        btype, csize, usize = struct.unpack_from("<BII", raw, 0)
        payload = raw[9:9 + csize]
        if btype == 4:
            payload = dz.decompress(payload, max_output_size=usize)
        elif btype != 0:
            raise ValueError(f"{path}: block {i} unknown type {btype}")
        if len(payload) != usize:
            raise ValueError(f"{path}: block {i} size mismatch")
        blocks.append((btype, payload))
    return version, blocks


def write_container(path, version, blocks):
    cz = zstandard.ZstdCompressor(level=ZSTD_LEVEL)
    chunks, offs, pos = [], [], 0
    for btype, payload in blocks:
        body = cz.compress(payload) if btype == 4 else payload
        chunk = struct.pack("<BII", btype, len(body), len(payload)) + body
        offs.append(pos)
        chunks.append(chunk)
        pos += len(chunk)
    offs.append(pos)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", MAGIC, version, len(blocks)))
        f.write(struct.pack(f"<{len(offs)}I", *offs))
        for c in chunks:
            f.write(c)


# ---------------------------------------------------------------- text block
def is_text_block(payload):
    return len(payload) >= 24 and struct.unpack_from("<I", payload, 16)[0] == TEXT_SIG


def parse_text_block(payload):
    """Return (cap, slots_start, entries) where entries = [(slot_index, key_bytes, text_bytes)]."""
    cap = struct.unpack_from("<Q", payload, 0)[0]
    ctrl = payload[24:24 + cap]
    slots_start = (24 + cap + 16 + 7) & ~7  # ctrl = cap+16 bytes, slots 8-aligned
    entries = []
    for j in range(cap):
        if ctrl[j] & 0x80:
            continue
        p = slots_start + 16 * j
        key = payload[p:p + 8]
        rel, ln = struct.unpack_from("<II", payload, p + 8)
        s = p + 8 + rel
        entries.append((j, key, payload[s:s + ln]))
    return cap, slots_start, entries


def build_text_block(payload, replace):
    """Rebuild a text block. `replace` maps key_bytes -> new text bytes.

    Mirrors the game's own writer: strings keep their original storage order
    (insertion order, not slot order) and identical strings share one copy.
    Empty slots are left untouched (their length is 0 and ctrl marks them empty).
    """
    cap, slots_start, entries = parse_text_block(payload)
    text_start = slots_start + 16 * cap
    out = bytearray(payload[:text_start])

    def orig_start(e):
        p = slots_start + 16 * e[0]
        return p + 8 + struct.unpack_from("<I", payload, p + 8)[0]

    texts = bytearray()
    placed = {}  # text bytes -> absolute position
    for j, key, text in sorted(entries, key=lambda e: (orig_start(e), e[0])):
        text = replace.get(key, text)
        pos = placed.get(text)
        if pos is None:
            pos = text_start + len(texts)
            placed[text] = pos
            texts += text
        p = slots_start + 16 * j
        struct.pack_into("<II", out, p + 8, pos - (p + 8), len(text))
    return bytes(out + texts)


def iter_entries(blocks):
    for btype, payload in blocks:
        if is_text_block(payload):
            for _, key, text in parse_text_block(payload)[2]:
                yield key, text


# ---------------------------------------------------------------- tsv
def esc(s):
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def unesc(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"\\": "\\", "t": "\t", "n": "\n", "r": "\r"}.get(n, "\\" + n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def load_tsv(path):
    m = {}
    with open(path, encoding="utf-8", errors="surrogateescape", newline="\n") as f:
        header = f.readline()
        if not header.startswith("key\t"):
            raise ValueError(f"{path}: expected header 'key<TAB>text'")
        for ln, line in enumerate(f, 2):
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            key, _, text = line.partition("\t")
            if len(key) != 16:
                raise ValueError(f"{path}:{ln}: bad key {key!r}")
            m[bytes.fromhex(key)] = unesc(text).encode("utf-8", "surrogateescape")
    return m


# ---------------------------------------------------------------- commands
def cmd_export(src, dst):
    _, blocks = read_container(src)
    n = 0
    with open(dst, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as f:
        f.write("key\ttext\n")
        for key, text in iter_entries(blocks):
            f.write(f"{key.hex()}\t{esc(text.decode('utf-8', 'surrogateescape'))}\n")
            n += 1
    print(f"exported {n} entries -> {dst}")


def cmd_patch(src, tsv, dst):
    version, blocks = read_container(src)
    repl = load_tsv(tsv)
    keys_in_file = set()
    changed = 0
    new_blocks = []
    for btype, payload in blocks:
        if is_text_block(payload):
            ents = parse_text_block(payload)[2]
            local = {}
            for _, key, text in ents:
                keys_in_file.add(key)
                if key in repl and repl[key] != text and text != b"\xff":  # 0xFF in a _diff = no override, keep it
                    local[key] = repl[key]
            if local:
                changed += len(local)
                payload = build_text_block(payload, local)
        new_blocks.append((btype, payload))
    write_container(dst, version, new_blocks)
    missing = len(set(repl) - keys_in_file)
    print(f"patched {changed} entries ({len(repl)} in tsv, {missing} keys not in this file) -> {dst}")


def cmd_verify(src):
    version, blocks = read_container(src)
    n_text = n_ent = 0
    for i, (btype, payload) in enumerate(blocks):
        if not is_text_block(payload):
            continue
        n_text += 1
        rebuilt = build_text_block(payload, {})
        if rebuilt != payload:
            raise SystemExit(f"FAIL: block {i} differs after rebuild")
        n_ent += len(parse_text_block(payload)[2])
    print(f"OK: {len(blocks)} blocks ({n_text} text), {n_ent} entries rebuild byte-identical")


def main(argv):
    if len(argv) >= 2:
        sys.stdout.reconfigure(encoding="utf-8")
        cmd, args = argv[1], argv[2:]
        if cmd == "export" and len(args) == 2:
            return cmd_export(*args)
        if cmd == "patch" and len(args) == 3:
            return cmd_patch(*args)
        if cmd == "verify" and len(args) == 1:
            return cmd_verify(*args)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
