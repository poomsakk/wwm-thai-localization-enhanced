# Subagent task: translate ONE chunk (Chinese → Thai)

Project: the root of this repo. Your chunk number NNNN is given in your prompt.

> Orchestrator (not the agent): claim chunks with `python -I tools/next_chunk.py [--range FROM TO]`,
> start each agent with "Follow docs/AGENT_CHUNK_TASK.md; your chunk is NNNN; scratchpad: <dir>".
> When an agent finishes, `python -I tools/next_chunk.py NNNN` checks it, releases its claim and
> claims the next chunk. Keep ~10 agents running. Afterwards: `tools/name_pass.py`, `build_mod.bat`.

1. Read docs/STYLE_GUIDE.md and docs/AGENT_TRANSLATION_GUIDE.md fully first and follow them exactly
   (workflow, name priority, special tokens, classics/poem conventions, fixed long_text names).
   glossary/series_names.tsv always wins for names.
2. Show the chunk: `python -I tools/show_chunk.py NNNN`.
3. Collect every proper name/term in the chunk and look them all up in ONE call:
   `python -I tools/name_lookup.py 名1 名2 ...` and use the `-> use:` pick
   (except where the guide's fixed list says otherwise).
4. Write work/queue/NNNN.out.tsv: header `id\tth`, then `id<TAB>thai` per item.
   - literal `\n` for newlines; same newline count as the source incl. blank lines and leading/trailing `\n`
   - keep #X…#E colour codes (incl. hex forms like #8c5823… — the code is 6 hex digits, text follows), $N, $D$F2$E,
     {placeholders}, <LINK>/<IMAGE> tags byte-for-byte, ⬛ ䷂ ▆
   - full-width ； and ASCII ; counts must match the source
   - copy `@en:` lines unchanged; copy leading/trailing spaces from the source
   - helper scripts/drafts go in the scratchpad given in your prompt, names prefixed `agentNNNN_`;
     in Python call sys.stdout.reconfigure(encoding='utf-8') (python -I ignores PYTHONIOENCODING)
5. Validate: `python -I tools/translate.py check NNNN` and fix until `N/N lines, 0 problems`.

Rules:
- Translate every item fully and naturally — no summarizing, no skipped lines.
- Do NOT edit any other file (glossary, guides, DB, other chunks). Do NOT run import / pick / build.
  Do NOT delete the NNNN.inchat marker.
- Fixed names: 不见山 เขาปู้เจี้ยน, 寄棺主 จี้กวนจู่, 梦傀 หุ่นเชิดนิทรา, 孤云 กูหยุน, 万相集 สมุดหมื่นภาพ,
  契丹 ชี่ตาน, 醉仙月 เดือนเซียนเมา, 乘漪濯心 ล่องระลอกล้างใจ.
- Bracket text like [#送花], [#微笑], <小声>, <心想> is plain text (EN and old Thai translate it): translate it. Only numeric emote codes like [#201] stay as-is.
- Surname 翟 = ไจ๋ (not จ๋าย / ตี๋).
- Northwestern dialect: 鹅/额 used as "I" (我) = ข้า, 额达 = พ่อข้า — not "goose".
- Buddhist/Taoist dharma names of characters (e.g. monks 普通, 通畅) are names: transliterate (ผู่ทง, ทงชั่ง), never translate their meaning.
- 君不见 as a person (the thief 盗圣君不见) = จวินปู้เจี้ยน; only the poem phrase 君不见… means "เจ้าไม่เห็นหรือ".

Final reply — keep it SHORT (max ~8 lines): the exact check line, then at most 5 bullets:
new important names you invented (zh = th) and lines you are unsure about.
