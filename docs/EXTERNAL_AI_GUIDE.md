# ใช้ AI เจ้าอื่นช่วยแปล (ChatGPT, Gemini, DeepSeek, Grok, LLM ในเครื่อง ฯลฯ)

ระบบของโปรเจกต์นี้ทำงานผ่าน **ไฟล์** ไม่ผูกกับ AI เจ้าไหน
AI ตัวไหนก็ได้ ขอแค่รับไฟล์ `work\queue\NNNN.tsv` แล้วคืนไฟล์ `work\queue\NNNN.out.tsv` ในรูปแบบที่ถูกต้อง
จากนั้น `build_mod.bat` จะตรวจ รวมชื่อให้ตรงกัน และนำเข้าให้เหมือนงานของ Claude ทุกอย่าง

```
NNNN.tsv  ──►  AI เจ้าไหนก็ได้  ──►  NNNN.out.tsv  ──►  check  ──►  build_mod.bat
(ต้นฉบับ)                            (คำแปล)          (ตรวจ)      (นำเข้า+บิวด์+ติดตั้ง)
```

## ขั้นที่ 1: เลือกก้อนที่จะแปล
ดับเบิลคลิก `build_mod.bat` บรรทัดท้ายจะบอกก้อนที่รอแปล (เช่น `next: 0117, 0128, ...`)
**อย่าแปลก้อนเดียวกันพร้อมกันสองเจ้า** เพราะเจ้าที่บันทึกทีหลังจะทับของเจ้าแรก
ถ้าต้องการแบ่งงาน ให้จดไว้ว่าเจ้าไหนทำก้อนไหน

## ขั้นที่ 2: ส่งให้ AI แปล
1. เปิด `work\queue\NNNN.tsv` ด้วย Notepad แล้วคัดลอกทั้งไฟล์ (หรืออัปโหลดเป็นไฟล์ถ้า AI รองรับ)
2. ถ้า AI รับไฟล์แนบได้ ให้แนบ `docs\STYLE_GUIDE.md` และ `docs\AGENT_TRANSLATION_GUIDE.md` ไปด้วย คุณภาพจะดีขึ้นมาก
3. วาง **prompt ด้านล่าง** ตามด้วยเนื้อหาไฟล์
4. ก้อนใหม่มีแค่ 30 บรรทัด ส่งได้ทีเดียวทั้งก้อน

### Prompt (คัดลอกทั้งกล่อง)
```
You translate game text of "Where Winds Meet" (燕云十六声), a wuxia RPG set in 10th-century China, from Chinese into Thai.

INPUT: tab-separated lines: id, zh, en, th_old, terms
- zh = source, translate from this. en = official English, a hint only. th_old = old Thai, often wrong.
- terms = "中文=ไทย; ..." glossary entries found in the line. You MUST use these Thai renderings.
- "\n" inside text means a line break. Keep it written as \n.

OUTPUT: only tab-separated lines "id<TAB>thai", one per input id, same ids, first line "id<TAB>th". No explanations, no code fences, no extra columns.

RULES
- UI, buttons and labels: short modern Thai, no trailing period.
- Character speech: pronouns ข้า / เจ้า / ท่าน with modern sentence structure. Never ฉัน คุณ เธอ ครับ ค่ะ.
- Game terms use loanwords: สกิล ดาเมจ บัฟ ดีบัฟ คูลดาวน์ คริติคอล ชิลด์ สตามินา HP EXP เลเวล บอส ดันเจี้ยน.
- Keep these in English: Bellstrike, Stonesplit, Bamboocut, Silkbind, Super Armor, Battle Pass, Elite, Co-op, Campaign. Put spaces around English words.
- Person names: Mandarin transliteration (e.g. 陈 เฉิน, 刘 หลิว, 黄 หวง, 王 หวัง, 张 จาง).
- Place / sect names: transliterated name + Thai type word: 门 สำนัก, 楼/馆/阁 หอ, 帮 พรรค, 山 เขา, 谷 หุบเขา, 河 แม่น้ำ, 湖 ทะเลสาบ, 城 เมือง.
- Quest, skill, item and set titles with a clear meaning: translate the meaning, short and evocative.
- Copy exactly: color codes like #Y...#E #H...#E (same count), {0} {} %s %d, the | separator (translate both sides), and the number of \n.
- No Chinese characters may remain. Conventions: N段 = ขั้นที่ N, N重 = ชั้นที่ N, 技能N = สกิล N, 官兵 = นายทหาร, 和鸣 = กาชา.

Translate all lines below:
```

## ขั้นที่ 3: บันทึกผล
1. คัดลอกคำตอบของ AI ทั้งหมด
2. สร้างไฟล์ `work\queue\NNNN.out.tsv` (เลขเดียวกับต้นฉบับ) ใน Notepad แล้ววางผล
3. **บันทึกเป็น UTF-8** (Notepad: Save As → Encoding: UTF-8)
4. ตรวจว่าแต่ละบรรทัดคั่นด้วย **Tab** ไม่ใช่ช่องว่าง (บางเว็บแชตแปลง Tab เป็นช่องว่าง ถ้าเกิด ให้ขอ AI ส่งเป็น code block หรือไฟล์)

## ขั้นที่ 4: ตรวจก่อนนำเข้า
เปิด Command Prompt ในโฟลเดอร์โปรเจกต์ แล้วพิมพ์ (ใส่เลขก้อนกี่ก้อนก็ได้)
```
python -I tools\translate.py check 0117 0128
```
ผลที่ดีคือ `300/300 lines, 0 problems` ถ้ามีปัญหาจะบอกเป็นบรรทัด เช่น
- `missing`: AI ข้ามบรรทัดนั้น ให้ขอ AI แปลเฉพาะ id นั้นเพิ่ม
- `chinese_left`: ยังมีตัวจีนเหลืออยู่
- `tokens [...] != [...]`: โค้ดสีหรือตัวแปรหาย
- `not 'id<TAB>text'`: รูปแบบผิด (มักเป็นเพราะ Tab กลายเป็นช่องว่าง)

ไม่ต้องแก้ทุกจุดให้หมดก่อนนำเข้าก็ได้ บรรทัดที่ไม่ผ่านจะถูกติดสถานะ `needs_fix` และจะไม่ถูกใส่ลงเกม

## ขั้นที่ 5: บิวด์
ปิดเกม แล้วดับเบิลคลิก `build_mod.bat` ตามปกติ
ระบบจะปรับชื่อชุด/สายวิชาให้ตรงกับ `glossary\series_names.tsv` ให้อัตโนมัติก่อนนำเข้า

## คำแนะนำ
- **ลองก้อนเดียวก่อน** แล้วเทียบคุณภาพกับงานที่ทำไปแล้ว (เปิด `compare_old_vs_new.csv` หรือเข้าเกมดู)
- AI แต่ละเจ้ามีสำนวนต่างกัน ถ้าใช้หลายเจ้า ให้แบ่งตามหมวด เช่น เจ้า A ทำ UI เจ้า B ทำคำอธิบาย คำแปลในหมวดเดียวกันจะได้ไม่ปนสำนวน
- ถ้า AI ตั้งชื่อชุดหรือไอเทมใหม่ที่ไม่ตรงกับของเดิม ให้เพิ่มลงใน `glossary\series_names.tsv` (คอลัมน์: จีน, ไทยที่ต้องการ, คำที่ต้องแทนที่) แล้วรัน `build_mod.bat` ใหม่
- **อย่าส่ง API key หรือข้อมูลส่วนตัว** ให้ AI ใด ๆ ส่งแค่เนื้อหาในไฟล์ `.tsv` ก็พอ

---

# Z.ai (GLM) แบบอัตโนมัติด้วยสคริปต์

ใช้ API ของ Z.ai แปลทีละก้อนให้อัตโนมัติ ไม่ต้องคัดลอกและวางเอง สคริปต์คือ `tools\zai_translate.py`
(ข้อมูล API ตรวจจากเอกสาร Z.ai เมื่อ 2026-11-13: base URL `https://api.z.ai/api/paas/v4/`, โมเดลหลัก `glm-5.3`)

## ตั้งค่าครั้งแรก
1. สมัครหรือล็อกอินที่ https://z.ai/model-api
2. เติมเงินที่ https://z.ai/manage-apikey/billing (ถ้าบัญชียังไม่มีเครดิต)
3. สร้าง API key ที่ https://z.ai/manage-apikey/apikey-list แล้วคัดลอกเก็บไว้ (**อย่าส่งให้ใคร และอย่าวางในแชต**)
4. ติดตั้งไลบรารี (ครั้งเดียว):
   ```
   pip install openai
   ```

## ทุกครั้งที่จะแปล
1. เปิด **Command Prompt** แล้วเข้าโฟลเดอร์โปรเจกต์
   ```
   cd /d <project folder>
   ```
2. ใส่ key (มีผลเฉพาะหน้าต่างนี้ ปิดหน้าต่างแล้ว key จะหายไป):
   ```
   set ZAI_API_KEY=วาง-key-ตรงนี้
   ```
3. ลองดูขนาดคำขอโดยไม่เสียเงิน:
   ```
   python -I tools\zai_translate.py 0117 --dry-run
   ```
4. แปลจริง (ใส่ได้หลายก้อน):
   ```
   python -I tools\zai_translate.py 0117
   ```
   สคริปต์ส่งครั้งละ 100 บรรทัด ถ้า AI ข้ามบรรทัดไหน จะส่งบรรทัดนั้นซ้ำให้เองอีก 2 รอบ แล้วเขียนผลเป็น `work\queue\0117.out.tsv`
5. ตรวจผล:
   ```
   python -I tools\translate.py check 0117
   ```
6. ปิดเกม แล้วดับเบิลคลิก `build_mod.bat`

## ตัวเลือกเพิ่มเติม
- เปลี่ยนโมเดล: `--model glm-5.3-flash` (ชื่อรุ่นอื่น ๆ ดูได้จากหน้าเอกสารของ Z.ai)
- แปลก้อนที่มี `.out.tsv` อยู่แล้วซ้ำ: `--force` (ปกติสคริปต์จะไม่เขียนทับ)
- ถ้าใช้ **GLM Coding Plan** แทนการเติมเงิน: plan นี้ใช้ URL คนละตัว (`https://api.z.ai/api/coding/paas/v4`) ให้แก้ค่า `BASE_URL` ในบรรทัดต้น ๆ ของสคริปต์

## คำแนะนำ
- **ลองก้อนเดียวก่อน** แล้วเทียบคุณภาพกับงานของ Claude ด้วย `compare_old_vs_new.csv` (สร้างใหม่ได้โดยถาม Claude) หรือเข้าเกมดู
- ทุกคำขอแนบ Style Guide, คู่มือ และรายชื่อชุด/ไอเทมไปด้วย (ประมาณ 14,000 ตัวอักษร) เพื่อให้สำนวนและชื่อตรงกับงานเดิม ค่าใช้จ่ายส่วนนี้จึงเพิ่มขึ้นทุกคำขอ
- ดูค่าใช้จ่ายจริงได้ที่หน้า billing ของ Z.ai หลังลองก้อนแรก
