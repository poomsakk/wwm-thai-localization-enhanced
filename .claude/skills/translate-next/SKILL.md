---
name: translate-next
description: Translate ONE waiting chunk of Where Winds Meet text (Chinese -> Thai) directly in this chat, without subagents or the API, then validate it. Use when the user types /translate-next.
disable-model-invocation: true
---

# Translate the next chunk in this chat

Work in `D:\wwm-thai-localization-enhance`. Translate exactly **one** chunk yourself, in this conversation.
**Do not spawn subagents. Do not call the Claude API. Do not run build_mod.bat or import anything.**

## Steps
1. Claim a chunk (takes one from the end of the queue so it never collides with API batches):
   ```
   python -I tools\translate.py pick
   ```
   It prints a chunk name such as `0964` and marks it `NNNN.inchat`. If it prints nothing, tell the user the queue is empty and stop.
   If the user named a chunk after the command (e.g. `/translate-next 0300`), use that chunk instead and skip `pick`.
2. If you have not read them earlier in this conversation, read:
   - `docs\STYLE_GUIDE.md`
   - `docs\AGENT_TRANSLATION_GUIDE.md` (rules + fixed names at the end)
   - `glossary\series_names.tsv`
   Otherwise reuse what you already know; do not re-read.
3. Read `work\queue\NNNN.tsv` (columns: id, zh, en, th_old, terms; `\n` = escaped line break).
4. Translate every line following the guides (terms column is binding). For person names you are unsure of, run
   `python -I tools\translit.py <names...>` once for the whole chunk.
5. Write `work\queue\NNNN.out.tsv`: header `id<TAB>th`, one line per input id, keep `\n` escaped as `\n`.
   For a large chunk you may write it in two or three parts (write the file, then append with Edit) to keep each write manageable.
6. Validate:
   ```
   python -I tools\translate.py check NNNN
   ```
   Fix every reported problem in the .out.tsv and re-run until it shows `0 problems`.
7. Delete the claim marker `work\queue\NNNN.inchat`.
8. Report to the user in Thai, briefly: chunk name, line count, check result, 2–3 notable translation choices,
   and remind them that `build_mod.bat` puts it into the game. Add any new fixed name to the end of
   `docs\AGENT_TRANSLATION_GUIDE.md` (and to `glossary\series_names.tsv` if another rendering already exists).
