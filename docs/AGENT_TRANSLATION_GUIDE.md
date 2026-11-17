# Agent Translation Guide (chunk workflow)

You translate chunk files of Where Winds Meet (燕云十六声) game text from Chinese into Thai.

## Before you start
1. Read `docs\STYLE_GUIDE.md` fully. It is binding.
2. Look at a finished chunk of the same kind to match its conventions: `work\queue\0001.out.tsv` (UI),
   `work\queue\1300.out.tsv` (dialogue), `work\queue\1530.out.tsv` / `1541.out.tsv` (long_text: classics, poems, letters).
3. Translate ONLY the chunk numbers you were given. Never run `translate.py pick`, never create/delete
   `.inchat` / `.imported` files, never touch other agents' chunks.

## Per-chunk workflow (do every step)
1. Read the chunk: `python -I tools\show_chunk.py NNNN` (one line per item: id, zh, glossary terms).
2. Names: collect every proper name / item / skill / place / sect name in the chunk and look them all up
   in ONE call: `python -I tools\name_lookup.py 名字1 名字2 ...`. Use the `-> use:` line. Never trust a single
   DB row alone — the most-used rendering wins (see "Name priority" below).
3. Write `work\queue\NNNN.out.tsv` (format below).
4. Check: `python -I tools\translate.py check NNNN` → must say `N/N lines, 0 problems`. Fix and re-check until it does.
   Typical failures: `newline_count` (a `\n` or blank line `\n\n` missing/extra — also leading `\n` at the very
   start and trailing `\n` at the very end), a missing line, a leftover Chinese character, a changed token.
5. Report back only: chunk numbers, `0 problems` confirmation, and any new names you had to invent (zh = th).

## Name priority
1. `glossary\series_names.tsv` (fixed names; variants listed there are wrong — never use them).
2. `glossary\glossary.tsv` approved terms (the `terms` column of the chunk) — must be used in system/UI text.
3. Otherwise the rendering used most often in finished translations (`name_lookup.py` counts it).
4. New name: Mandarin transliteration via `tools\translit.py` + translated type word (see Rules).

### Glossary hints that are WRONG in narrative text (story, letters, poems, classics)
The `terms` column is generated automatically and is meant for UI/system text. In narrative use natural Thai:
- 经验 = ประสบการณ์ (not EXP) · 沉默 = เงียบ / นิ่งเงียบ (not ไซเลนซ์) · 无敌 = ไร้เทียมทาน (not อมตะ)
- 多人 = คนมากมาย (หลายผู้เล่น only for multiplayer mode) · 击飞 in story = กระเด็น
- 镇守 as a verb (guard a city) = รักษาการณ์ / ปกป้อง; 镇守 as the game mode = ด่านพิทักษ์ (user decision; boss = บอสด่านพิทักษ์)
- 沉吟 = ครุ่นคิด (verb); only the person 季沉吟 = จี้เฉินอิ๋น. 天上来 as the place = เทียนซ่างไหล, but in poems (黄河之水天上来) = มาจากฟ้า/สวรรค์. 伏马庄 หมู่บ้านฝูหม่า, 怒马庄 หมู่บ้านนู่หม่า.
- 继续/离开/开始/选择/询问/控制/完成 etc. → whatever reads naturally; the literal UI word is not required.

### Names fixed in the long_text work (reuse exactly)
User decisions: 不见山 = เขาปู้เจี้ยน (do not change), 镇守 (mode) = ด่านพิทักษ์.
Sects/places: 狂澜 ขวางหลาน, 醉花阴 จุ้ยฮวาอิน, 绣金楼 หอซิ่วจิน, 九流门 สำนักจิ่วหลิว, 墨山道 ทางเขาม่อ, 墨门 สำนักม่อ,
文津馆 หอเหวินจิน, 梨园 คณะหลีหยวน, 青溪 ชิงซี, 天泉 เทียนเฉวียน, 孤云 กูหยุน, 玄元教 ลัทธิเสวียนหยวน, 无忧帮 พรรคอู๋โยว,
鬼市(子) ตลาดผี, 不羡仙 ปู้เซี่ยนเซียน, 神仙渡 ท่าเรือเทพเซียน, 樊楼 หอฝาน, 未央城 เมืองเว่ยยาง, 飞天城 เมืองเฟยเทียน,
晦谷 หุบเขาฮุ่ย, 墨城 เมืองม่อ, 涌泉镇 เมืองหย่งเฉวียน, 天水集 ตลาดเทียนสุ่ย, 角门里 เจี่ยวเหมินหลี่, 活人医馆 โรงหมอฮัวเหริน,
解忧司 สำนักคลายทุกข์, 十六巷 ตรอกสิบหก, 燕北盟 พันธมิตรเยียนเป่ย, 归义军 กองทัพกุยอี้, 安西 อานซี, 河西 เหอซี, 凉州 เหลียงโจว,
开封 ไคเฟิง, 杭州 หางโจว, 清河 ชิงเหอ, 滹沱 หูถัว, 青州 ชิงโจว, 长安 ฉางอัน, 江南 เจียงหนาน.
People/address: 游侠 จอมยุทธ์พเนจร, 少侠 ท่านจอมยุทธ์ (not จอมยุทธ์น้อย), 大侠 ยอดจอมยุทธ์, 侠客 จอมยุทธ์, 少东家 นายน้อย (the player may be female: never คุณชายน้อย), 掌柜 เถ้าแก่,
师父 ท่านอาจารย์, 师兄/师姐 ศิษย์พี่/ศิษย์พี่หญิง, 师弟/师妹 ศิษย์น้อง/ศิษย์น้องหญิง, 契丹 ชี่ตาน, 虏人 พวกข้าศึก.
Items/systems: 长鸣玉 หยกเสียงก้อง, 长鸣珠 ไข่มุกเสียงก้อง, 袅袅之音 เสียงแว่วกังวาน, 万相集 สมุดหมื่นภาพ, 寄棺主 จี้กวนจู่, 梦傀 หุ่นเชิดนิทรา, 妙妙喵 เมี่ยวเมี่ยวเหมียว,
妙妙庙 ศาลเจ้าเมี่ยวเมี่ยว, 莲莲荷包 ถุงหอมดอกบัว, 福龟 เต่านำโชค, 演武 แสดงยุทธ์, 群策 วางแผนร่วมกัน, 止戈 อารีน่า,
东方第一枝 (gazette) 《กิ่งแรกแห่งบูรพา》, 《燕云十六声》 = 《Where Winds Meet》, 燕云 (customer service etc.) เยียนหยุน,
rarity: 绝世 ตำนาน, 非凡 พิเศษ, 珍品 ของล้ำค่า. Standard letter openings: 游侠亲启 = ถึงจอมยุทธ์พเนจร:, 见字如面 = เห็นอักษรดั่งเห็นหน้า.

### Special text patterns (keep exactly)
- Lines starting with `@en:` (no Chinese source exists) — copy the whole line unchanged.
- Filler repeated N times (e.g. 数据获取中…, 时装文案包装信息加载中...) — translate once and repeat exactly N times.
- `<LINK …>…</LINK>` and `<IMAGE …></IMAGE>`: keep the tag text byte-for-byte (including `{uid}`, `{pid}`, `{hostnum}`,
  `color='255;255;255')'` with its odd quote); translate only the visible link text between the tags.
- Color codes incl. hex forms: `#Y…#E`, `#H…#E`, `#G…#E`, `#4d734d…#E`, `#ffc89c…#E`, `#8c5823…#E`, `#aee5ae20#E`
  (here `20` is the value inside the code). Same count and position. Game tokens `$N`, `$D`, `$D$F2$E`, `$G20902206$E`, `{}`.
- Full-width `；` count must equal the source; ASCII `;` count must equal the source. `：` may become `:`.
- Keep symbols that are not Chinese characters: `⬛`, `███`, `▆`, hexagram signs like `䷂`, `○`/`〇`, `【】`, `「」`, `《》`, `——`, `……`.
- Leading spaces / indentation at line starts (letters) and blank lines: keep them. Trailing spaces are fixed by tools.
- Puns on Chinese characters: translate the meaning and, if needed, explain the pun briefly in the sentence
  (e.g. 笼中雀 → “ตัวอักษรกรงขังนก ถ้ารื้อหลังคาไม้ไผ่ด้านบนออก ก็กลายเป็นตัวอักษรมังกร”).

### Classics and poems (long_text)
- Translate faithfully into readable modern Thai; one output line per source line (poem lines stay separate).
- Titles of chapters/poems: translate the meaning; author names = transliteration (李白 หลี่ไป๋, 杜甫 ตู้ฝู่, 白居易 ไป๋จวีอี้).
- Book titles in 《》: transliterate (《史记》《สื่อจี้》, 《左传》《จั่วจ้วน》); Shijing sections 国风·X风 = กั๋วเฟิง·Xเฟิง.
- Chunqiu style: 公 = องค์กง, X侯 = Xโหว, X伯 = Xป๋อ, 天王 = โอรสสวรรค์, 王正月 = เดือนอ้ายตามปฏิทินของโอรสสวรรค์;
  sexagenary days transliterated (癸亥 กุ่ยไฮ่, 丁巳 ติงซื่อ, 甲子 เจี่ยจื่อ).
- Rites texts: 主人 เจ้าภาพ, 宾 แขก, 尸 ผู้แทนผู้ตาย, 祝 ผู้อ่านคำอธิษฐาน, 宗人 ผู้ดูแลพิธีตระกูล; ranks 卿 เสนาบดี,
  中/下大夫 ขุนนางชั้นกลาง/ล่าง, 上/中/下士 ซื่อชั้นสูง/กลาง/ล่าง, 府 เจ้าหน้าที่คลัง, 史 เสมียน, 胥 หัวหน้าคนงาน, 徒 คนงาน.

## Input
`work\queue\NNNN.tsv` — tab separated, header `id zh en th_old terms`
- `zh` = source (translate from this). `en` = official English (context hint, often loose).
- `th_old` = old official Thai — often wrong/inconsistent; reuse only when correct and in style.
- `terms` = `中文=ไทย; ...` glossary entries found in this line. **You must use these renderings.**
- Text fields are escaped: `\n` = newline, `\t` = tab, `\\` = backslash. Keep escapes in your output the same way.

## Output
Write `work\queue\NNNN.out.tsv`:
```
id	th
1	สนทนา
4	ขอตัวลา
```
- UTF-8, header `id<TAB>th`, exactly one line per input id, same ids, nothing else.
- Do not edit any other file. Do not run the import tool. Do not touch the database.

## Rules (summary — STYLE_GUIDE.md wins on conflict)
- UI / buttons / labels: short, modern Thai, no wuxia pronouns, no trailing period.
- Dialogue: ข้า / เจ้า / ท่าน, modern sentence structure; never ฉัน/คุณ/เธอ/ครับ/ค่ะ in character speech.
- Keep technical tokens exactly: `#Y…#E` / `#H…#E` color codes (same count), `{}` `{0}` `{name}`, `%s` `%d`, `\n` count, and `|` (male|female — translate both sides).
- No Chinese characters may remain in the output.
- Loanwords: system/combat terms per glossary (สกิล, ดาเมจ, บัฟ, คูลดาวน์, HP, เลเวล...). English as-is for: Bellstrike, Stonesplit, Bamboocut, Silkbind, Super Armor, Battle Pass, Elite, Co-op. Put spaces around English words inside Thai text.
- Proper names of people/places: Mandarin transliteration. For consistency **run the project tool** (many names in one call):
  `python -I tools\translit.py 陈子奚 江无浪 冯继升`
  Use its output for person names. Fix only obvious polyphone errors (e.g. surname 单 = ซ่าน).
- Famous historical figures / deities with an established Thai name keep it: 秦始皇 = จิ๋นซีฮ่องเต้, 孙武 = ซุนวู, 刘邦 = หลิวปัง, 孔子 = ขงจื๊อ, 观音 = กวนอิม, 关羽 = กวนอู.
- Old-official Thai that only transliterated a meaningful item/series name (e.g. 金错 = จินชั่ว) → translate the meaning (金错 = ฝังทอง, 绝尘 = ทิ้งธุลี) and keep that rendering for the whole series.
- If the source has an unbalanced color code (e.g. `#R` without `#E`), keep it exactly as in the source.
- Places / sects / organisations: transliterated name + translated type word (门 สำนัก, 楼/馆/阁 หอ, 帮 พรรค, 宫 ตำหนัก, 山 เขา, 谷 หุบเขา, 河/江 แม่น้ำ, 湖 ทะเลสาบ, 城 เมือง, 洞 ถ้ำ, 池 สระ). E.g. 晦谷 = หุบเขาฮุ่ย, 无忧洞 = ถ้ำอู๋โยว.
- Titles of quests / events / skills / items with clear meaning: translate the meaning, short and evocative (e.g. 乘龙弄月 = ขี่มังกรหยอกจันทร์, 夜行刀 = ดาบท่องราตรี).
- Kinship / address + name: 赵大哥 = พี่ใหญ่จ้าว, 周叔 = ลุงโจว, 小八 = เสี่ยวปา.

## Conventions fixed in chunk 0001 (reuse them)
| zh | th |
|---|---|
| N段 (Stage N) | ขั้นที่ N |
| N重 (Tier N) | ชั้นที่ N |
| N级 (Level N) | เลเวล N (character/item level) |
| 技能N | สกิล N |
| 点按 {} / 长按 {} | แตะ {} / กดค้าง {} |
| 查看 / 查看详情 | ดู / ดูรายละเอียด |
| 前往X | ไปX (前往查看 = ไปดู, 前往探索 = ไปสำรวจ) |
| 官兵 | นายทหาร (大宋官兵 = นายทหารต้าซ่ง) |
| 百姓 | ชาวบ้าน |
| 捕快 | มือปราบ |
| 和鸣 | กาชา |
| 气血X | HP / โบนัส HP / ฟื้นฟู HP |
| 外功X | กายภาพ (外功防御 = ป้องกันกายภาพ, 外功穿透 = เจาะเกราะกายภาพ) |
| 会意率 | อัตรา Affinity |
| 输出 (DPS role) | DPS |
| 大宋 | ต้าซ่ง |
| 观音 | กวนอิม |

## Quality bar
Natural Thai a player understands at a glance; consistent terminology; correct meaning from the Chinese. When unsure about a name, transliterate rather than invent a meaning.

## Series / set / weapon-art names already fixed (reuse exactly)
Equipment sets (meaning): 烟柳 หมอกหลิว, 飞隼 เหยี่ยวบิน, 鹰扬 อินทรีผงาด, 时雨 ฝนต้องฤดู, 燕归 นางแอ่นคืนรัง, 撼天 สะเทือนฟ้า, 裁云 ตัดเมฆ, 连星 ร้อยดารา, 断岳 ผ่าขุนเขา, 玄甲 เกราะนิล, 浣花 ล้างบุปผา, 梨雪 หิมะสาลี่, 鸣珂 กระดิ่งหยก, 倾觞 เอียงจอก, 盈盏 จอกเต็ม, 尚义 เทิดธรรม, 桂月 จันทร์หอม, 江凝 สายน้ำนิ่ง, 玉斗 จอกหยก, 易相 แปรโฉม, 急风 ลมกรรโชก, 山倾 ภูผาถล่ม, 不知寒 ไม่รู้หนาว, 金错 ฝังทอง, 绝尘 ทิ้งธุลี, 惊沙 ทรายสะท้าน, 金鳞 เกล็ดทอง, 飞将 ขุนพลบิน.
Path sub-names: `Silkbind·หยก`, `Stonesplit·หนักแน่น`, `Bamboocut·ว่าว` / `Bamboocut·ธุลี`; 翊 = ปีก, 樽 = จอก.
Weapon-art suffixes: ·绝 (EX) = ·สุดยอด, ·锋 = ·คม, ·煌 = ·เจิดจรัส, ·英 = ·วีระ.
Stats: 最小X攻击 / 最大X攻击 = โจมตี X ต่ำสุด / โจมตี X สูงสุด.
Weapon arts (user decision 2026-11-17, enforced by series_names.tsv): 八方风雷枪 หอกวายุอสนีแปดทิศ, 九曲惊神枪 หอกเก้าคุ้งสะท้านเทพ, 十方破阵 ทลายค่ายสิบทิศ, 嗟夫刀法 เพลงดาบรำพัน, 积矩九剑 กระบี่เก้ากลเรขา, 千机索天 พันกลไกคว้าฟ้า, 粟子游尘 เชือกมรณะท่องธุลี, 粟子行云 เชือกมรณะเหินเมฆา, 千香引魂蛊 กู่พันกลิ่นเรียกวิญญาณ, 醉梦游春 ฝันเมาท่องวสันต์, 杏游草野 พัดซิ่งเริงทุ่ง, 青山执笔 ขุนเขาเขียวจรดพู่กัน, 悬身拳法 เพลงหมัดลอยตัว, 文动霓裳 อักษราร่ายอาภรณ์รุ้ง, 泥犁三垢 สามมลทินแห่งนรก, 无名剑法 เพลงกระบี่ไร้นาม, 无名枪法 เพลงหอกไร้นาม, 斩雪刀法 เพลงดาบฟันหิมะ, 九重春色 วสันต์เก้าชั้น, 明川药典 ตำรายาหมิงชวน, 天志垂象 เจตน์ฟ้าเผยนิมิต, 断水双诀 เคล็ดคู่ตัดสายน้ำ.
More fixed names: 浣花 ล้างบุปผา (not ซักบุปผา), ·绝 = ·สุดยอด (not ขั้นสุด), 么玉 เหยาอวี้, 敏 ความว่องไว, 心力 พลังใจ, 太平武墓 สุสานยุทธ์ไท่ผิง, 武德司 กรมอู่เต๋อ, 墨城 เมืองม่อ, 装备叠音 ซ้อนเสียงอุปกรณ์, 装备定音 ปรับเสียงอุปกรณ์, Silkbind·ปีก.
Inline link tags like `<名字|781|#C|21001>`: translate only the name part, keep `|781|#C|21001>` exactly.
Output must contain only Thai, Latin letters, digits and punctuation — check for stray characters from other scripts.
More fixed names: 天雷开悟 อสนีบรรลุธรรม, 无相攻击 โจมตีไร้รูป, 长鸣玉 หยกเสียงก้อง, 耶律 (Khitan surname) เยลวี่, 赵匡胤 จ้าวควงอิ้น, 孟子 เม่งจื๊อ, 家业 คฤหาสน์, 次三衡径数 วัดวิถีลำดับสาม (次二 ลำดับสอง, 内一 ลำดับในหนึ่ง). 调息 in skill text = คูลดาวน์.
More fixed names: 霁青 ฟ้าหลังฝน, 紫绶 แพรม่วง, 砺金 ทองขัด, ·凡 ·สามัญ, 东望连环 ชุดลูกโซ่ตงวั่ง, 摧城连环 ชุดลูกโซ่ทลายเมือง (·穿杨 ทะลุใบหลิว, ·神臂 แขนเทพ, ·连珠 ยิงต่อเนื่อง, ·精准 แม่นยำ), 藏音·X ซ่อนเสียง·X, 危寂 สงัดมรณะ, 颓山 ภูผาทลาย, 不肝境界 แดนไม่ต้องปั่น, 属性目标·N เป้าหมายค่าสถานะ·N. Surnames: 黄 หวง, 王 หวัง.
Use your own uniquely named helper scripts in the scratchpad (other agents run at the same time).
More fixed names: X之乐 = ความสุขแห่ง… (来仪 การมาเยือน, 开平 สันติ, 积善 การสั่งสมบุญ, 灵长 สรรพชีวิต, 显仁 การเผยเมตตา, 庆平 การฉลองสันติ, 永平 สันติยั่งยืน, 大武 ยุทธ์ยิ่งใหญ่, 昭德 การเชิดชูคุณธรรม, 终 บทสุดท้าย); 霞剑 กระบี่อรุณ, 老顽童 เฒ่าทารก, 凌波·X เหินคลื่น·X, 缚袴 กางเกงพันขา, 披膊 เกราะไหล่, 争籁 ประชันเสียง, 聆音 (gacha) กาชาสดับเสียง, 奇遇 การผจญภัย, 思路点 แต้มไอเดีย, 心防 ปราการใจ, 门客 แขกในสังกัด, 牙行 หอนายหน้า, 侠迹 วีรกรรม, 天雷开悟·玉/尘/影/威 อสนีบรรลุธรรม·อวี้/เฉิน/อิ่ง/เวย.
Path sub-names (after a path name) are translated by meaning: ·玉 หยก, ·钧 หนักแน่น, ·鸢 ว่าว, ·尘 ธุลี, ·翊 ปีก, ·樽 จอก, ·威 พลัง, ·霖 ฝน, ·风 ลม.
More fixed names: 红尘弓 ธนูโลกีย์, 风烟 ลมควัน, 缺月弓 ธนูจันทร์เสี้ยว, 岁骨弓 ธนูกระดูกกาล, 银河弓 ธนูทางช้างเผือก, 雪守 พิทักษ์หิมะ, 醉歌 เพลงเมามาย, 十方 สิบทิศ, 丹心 ใจภักดี, ·试用 ·ทดลองใช้, ·见识 ·ความรู้, ·格物 ·ศึกษา, ·拾遗 ·เก็บตก, 象功之乐 ความสุขแห่งการสรรเสริญคุณงาม, 烛影 เงาเทียน, 西楚霸王 ฌ้อปาอ๋อง, 魏武帝 โจโฉ, 大神 (NetEase app) ต้าเสิน.
More fixed names: 狂澜 (faction) ขวางหลาน, 归鸿 ห่านคืนรัง, 万仞山 ภูผาสูงตระหง่าน, 陇上烟 หมอกแดนหลง, 夜征人 ผู้ท่องราตรี, 关山月 จันทร์ด่านเขา, 曳月连环 ชุดลูกโซ่ลากจันทร์, 云伞 ร่มเมฆ, 画扇 พัดภาพ, 碎刃 ดาบแหลก, 羽林 องครักษ์, 辟邪 ขับมาร, 悬壶行会 สมาคมผู้รักษา, 文士行会 สมาคมบัณฑิต, 鬼神愁 สะพรึงเทพมาร, 观潮客 ผู้ชมคลื่น, 红线 (person) หงเซี่ยน.
More fixed names (also enforced by glossary\series_names.tsv): 雪夜定 ราตรีหิมะสงบ (雪夜 alone = ราตรีหิมะ), 云珑 เมฆหยก, 携玉龙 ถือมังกรหยก, 含光 แสงแฝง, 双鲤 ปลาคู่, 鸣镖 ลูกดอกเสียง, 动岳 สะเทือนภู, 舞绫鼓 กลองแพรร่ายรำ, 质朴X Xเรียบง่าย, 千莳余响 เสียงก้องพันฤดู, 万籁·X เสียงธรรมชาติ·X, 扫地童子 เด็กกวาดลาน, 长鸣珠 ไข่มุกเสียงก้อง, 横刀 ดาบเหิง, 庄客 คนงานไร่, 常驻 ถาวร, 论剑 ประลองยุทธ์, 福禄寿 ฮกลกซิ่ว.
More fixed names: ·归燕 ·นางแอ่นคืนรัง, 断水 ตัดธารา, 金错环 วงแหวนฝังทอง, ·诛 ·พิฆาต, 臂甲 เกราะแขน, 腿甲 เกราะขา, 天志垂象 เจตน์ฟ้าเผยนิมิต, 风摇夏 ลมไหวคิมหันต์, 武林造诣 ความเชี่ยวชาญยุทธภพ, 华裳帖 บัตรทดลองชุด, 霞 (rarity tier) อรุณ. Always check glossary\series_names.tsv before naming a set.
More fixed names: 抱玉 โอบหยก, 急风骤 พายุกระหน่ำ, 凌波步 ก้าวเหินคลื่น, 岳山倾 ขุนเขาเอนถล่ม, 御无缺 พิทักษ์ไร้ช่องโหว่, 破竹·风 Bamboocut·ลม, 鸣金·影 Bellstrike·เงา, 鸣金·虹 Bellstrike·รุ้ง, 唐歌 เพลงถัง, 春雷 อสนีวสันต์, 纵横剑 กระบี่ทั่วทิศ, 安西军 กองทัพอานซี (安西 alone อานซี).
