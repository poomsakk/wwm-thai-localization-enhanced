# Review notes from translation agents (check in Phase 4)

## Consistency
- 华 in names: translit tool gives หวา (rule), some lines use ฮวา (common usage). Decide one and normalise. (chunks 0001, 0042-0046)
- 长 polyphone in names (cháng vs zhǎng): tool may give จ่าง; agents hand-fixed some (李长贵 หลี่ฉางกุ้ย).
- 前往X: terms column says ไปยัง, agents use ไปX per 0001 convention — fine, but checker must not flag.
- 契丹 = ชี่ตาน, 吐蕃 = ถู่ปอ — add to glossary.
- Series names fixed: 金错 ฝังทอง, 绝尘 ทิ้งธุลี, 惊沙 ทรายสะท้าน, 金鳞 เกล็ดทอง, 飞将 ขุนพลบิน.

## Uncertain lines (src_id)
- 0022-0026: 16323/16549 葱明 pun; 16470 dialect; 16484/19508/19637 mahjong terms; 16599 朝九; 19006 百肆 (en Battlegroup); 19686 丈育; 19321 通便; 20333/20486 unbalanced #R.
- 0042-0046: 35699 知丶; 36401 小计 (name vs subtotal); 37733 汤 (en Yi); 36061 圣人不死; 38593 %m/%d order; 39770 %s%s级解锁; 35680/35696 NPC labels.
- 0012-0016: 8594 墩; 8777 杏游; 8916 俣俣神浒; 8865 哈是骑 pun; 8898 晏平生; 9083 不凉人; 10599/12048/10607 fragments; foreign names 9055/10422/11703 (อับบาส, บาบัค, ญาบิร).
- 0068-0072: 6213 孔雀谣 / 6243 千金朝玉 (en names differ); 6894 朱邪骨勒 (勒 เล่อ); 7774 么玉 (surname yāo?); 7852 子不语 = ขงจื๊อ.
- 0063-0067: inline link tags `<名|781|#C|…>` name part translated — verify in game (5118, 6046); 5062 malformed #Y codes copied; 4496 无我 (en Mythic) = ไร้ตัวตน?; 4881 大卷微身 (Volutefit). Normalised concurrent-agent differences (ซักบุปผา→ล้างบุปผา, ขั้นสุด→สุดยอด, เม่าอวี้→เหยาอวี้) and a stray Devanagari ह.
- 0058-0062: stack tokens 【威/虹/影/玉/尘/鸢/钧/霖/翊/樽/风】 transliterated (check 樽 จุน vs 钧 จวิน); 衡径数 skill names.
- 0073-0077: @en-only lines translated from English (8952,10021,11882...); 7921 平/7958 和/8233 默默 ambiguous; 黄 surname was หวาง in some outputs (tool fixed to หวง now) — normalise; 不肝境界 rendered two ways (ระดับไม่ฟาร์ม vs แดนไม่ต้องปั่น).
- 0083-0087: 18261 劫难度众伤害 guess; 15285 牵丝效果 (path vs thread); 15532 白露 name vs solar term; 转律/变音 new; 19408 裂石·钧 = Stonesplit·หนักแน่น assumed.
- 0088-0092: 大神 app = ต้าเสิน vs อธิษฐานเทพ (20542, 21884) align; 20206 索中丞 (中丞 title?); 天雷开悟·X stack tokens transliterated while path sub-names use meaning — decide one.
- 0098-0102: 狂澜 rendered ขวางหลาน and คลื่นคลั่ง across chunks — align to ขวางหลาน; 27118/27449 promo vs pet name; 云珑 เมฆหยก/จี้เมฆ, 辟邪 ขับมาร/ปี้เสีย both exist.
- 0108-0112: 霞 rarity = อรุณ assumed; 逗神/暗逗 inconsistent (โต้วเสิน vs ตัวตลกเงา); 29841 书期 guess; 36249 妙双十一 pet name.
- 0093-0097: 25876 $T(2014)。 trailing 。 removed; 35691 unbalanced codes; 28323/35199 属攻, 25155 外攻触发 guesses; ~300 lines template-filled (check a sample).
