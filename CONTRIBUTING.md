# สำหรับนักพัฒนาและผู้ช่วยแปล

เอกสารนี้สำหรับคนที่อยากช่วยแก้คำแปล หรือ build และออก release ของม็อดเอง
ถ้าแค่อยากติดตั้งม็อด ดู [README.md](README.md)

ภาพรวมทั้งระบบ (เกมเก็บข้อความยังไง, ไปป์ไลน์การแปล, การ build และอัปเดต) อยู่ใน [docs/OVERVIEW.md](docs/OVERVIEW.md)

## ส่งคำแปลมาช่วย (ง่ายที่สุด ไม่ต้องมีเกมหรือ Python)

1. แก้บรรทัดใน `translations/<ประเภท>.tsv` ได้เฉพาะคอลัมน์ `th` ห้ามแตะคอลัมน์ `zh`
2. คงรหัสพิเศษให้เหมือนต้นฉบับทุกตัว เช่น `#Y…#E`, `{0}`, `%s`, `\n`, `<LINK…>`
3. ชื่อเฉพาะต้องตรงกับ `glossary/series_names.tsv` และศัพท์ต้องตรงกับ `glossary/glossary.tsv`
4. เปิด Pull Request

กติกาภาษาอยู่ใน [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md)

ถ้าอยากเสนอเปลี่ยนชื่อเฉพาะ (เช่น ชื่อวิชา) ส่งมาเป็น **ชื่อจีน + ชื่อไทยใหม่** จะค้นได้แม่นที่สุด

## โครงสร้าง repo

| โฟลเดอร์ / ไฟล์ | เนื้อหา |
|---|---|
| `translations/` | คำแปลทั้งหมด `zh<TAB>th` แยกตามประเภท เป็นต้นฉบับของคำแปลที่ถืออยู่ใน git |
| `glossary/` | ชื่อเฉพาะ (`series_names.tsv`) และศัพท์ (`glossary.tsv`) |
| `tools/` | สคริปต์ Python: อ่าน/เขียนไฟล์ภาษาของเกม, ฐานข้อมูล, ตรวจคำแปล, ทำ release |
| `docs/` | คู่มือภาษา, การแปล และการ build |
| `release/` | ชุดติดตั้งสำหรับผู้เล่น (`.bat` + PowerShell + `README.txt`) |
| `setup.bat` / `build_mod.bat` / `update_game.bat` | งานหลักของนักพัฒนา (ดูข้างล่าง) |
| `local.cfg` | โฟลเดอร์เกมของเครื่องนี้ (ไม่อยู่ใน git) |
| `backup/`, `work/`, `dist/` | ไฟล์ต้นฉบับของเกม, ฐานข้อมูล, ผล build (ไม่อยู่ใน git เพราะใหญ่และเป็นข้อมูลของเกม) |

## เริ่มทำงานบนเครื่องใหม่ (clone ครั้งแรก / ล้างเครื่อง)

ต้องมี:

- เกมเวอร์ชัน **Steam** ที่เป็นภาษาไทยต้นฉบับ **ยังไม่ได้ลงม็อด** (ถ้าลงอยู่ ให้ Steam > Verify integrity ก่อน)
- Python 3.10+ (ติ๊ก "Add python.exe to PATH" ตอนติดตั้ง)

```bash
git clone https://github.com/poomsakk/wwm-thai-localization-enhanced.git
```

แล้วดับเบิลคลิก **`setup.bat`** ครั้งเดียว มันจะ:

1. ลงไลบรารี Python
2. หาโฟลเดอร์เกมจาก Steam แล้วบันทึกใน `local.cfg`
3. สำรองไฟล์ไทยต้นฉบับไว้ใน `backup\original` (ทั้ง `Package` และ `LocalData`)
4. สร้าง `work\wwm.db`
5. โหลดคำแปลทั้งหมดจาก `translations/`

## งานประจำ

| งาน | วิธี |
|---|---|
| build + ติดตั้งม็อดลงเกม | `build_mod.bat` (ดึงคำแปลที่เปลี่ยนใน git เข้า DB ก่อน แล้ว export `translations/` ให้เอง) |
| build อย่างเดียว ไม่แตะเกม | `build_mod.bat nocopy` |
| เกมอัปเดต | `update_game.bat` → แปลข้อความใหม่ (`translate.py chunks --new`) → `build_mod.bat` |
| เพิ่ม/แก้ชื่อเฉพาะ | แก้ `glossary/series_names.tsv` → `python -I tools/name_pass.py --apply` → `build_mod.bat` |
| แจกงานให้ subagent หลายตัว | `python -I tools/next_chunk.py [ก้อนที่เสร็จ]` (ดู [docs/AGENT_CHUNK_TASK.md](docs/AGENT_CHUNK_TASK.md)) |
| เก็บงานขึ้น GitHub | `git add -A` → `git commit -m "..."` → `git push` |

## ออก release

1. `build_mod.bat nocopy`
2. `python -I tools/make_release.py --version 2026.11.17.3`
   - ไม่มีเกม Steam ในเครื่อง: เพิ่ม `--game <โฟลเดอร์เกม>` เช่น `--game D:\wwm\wwm_lite` (ใช้อ่าน `Built.version` อย่างเดียว)
   - เลขเวอร์ชัน 2–4 ตัว ตั้งตามวันที่ ถ้าวันเดียวกันออกหลายรอบให้ต่อ `.2`, `.3`
3. สร้าง GitHub Release ใหม่ tag `v<เวอร์ชัน>` แล้วอัปโหลด **ทั้ง 2 ไฟล์** จาก `dist/<เวอร์ชัน>/`
   - `WWM-Thai-<เวอร์ชัน>.zip`
   - `manifest.txt` (play.bat / install.bat ของผู้เล่นใช้ไฟล์นี้หา release ที่ตรงกับเกม)

ผู้เล่นที่ติดตั้งไว้แล้วจะได้เวอร์ชันใหม่เองตอนกด Play (อัปเดตเฉพาะไฟล์ภาษา ไม่อัปเดตสคริปต์)
ถ้าแก้สคริปต์ใน `release/` ผู้เล่นต้องโหลด zip ใหม่แล้วรัน `install.bat` ทับ

## ชุดติดตั้งสำหรับผู้เล่น (release/)

| ไฟล์ | หน้าที่ |
|---|---|
| `install.bat` | หาเกม → เช็ก GitHub หาเวอร์ชันล่าสุดที่ตรงกับเกม → สำรองต้นฉบับ → ติดตั้ง |
| `play.bat` | Steam Launch Option (`"…\play.bat" %command%`) หรือ shortcut บน Desktop (Launcher ของเกม): เช็กอัปเดต + ซ่อมไฟล์ แล้วเปิดเกม |
| `uninstall.bat` | คืนไฟล์ต้นฉบับ ลบ shortcut |
| `wwm-thai.ps1` | ตรรกะทั้งหมด (Windows PowerShell 5.1, UTF-8 BOM, CRLF) |

ความปลอดภัย: แตะไฟล์เกมเฉพาะเมื่อ SHA256 ตรงกับ manifest เท่านั้น และอัปเดตจาก GitHub Releases ของ repo นี้เท่านั้น (ตรวจ SHA256 ของ zip ก่อนใช้)

แต่ละแพลตฟอร์ม:

- **Steam:** แก้ไฟล์ใน `Package\HD\oversea\locale`
- **Epic Games:** ไม่รองรับ (ตัดออกแล้ว ไม่มีโค้ดหาเกมหรือเปิดเกมผ่าน Epic)
- **Launcher ของเกม (standalone):** ไฟล์ภาษาอยู่ใน `LocalData\Patch\HD\oversea\locale`
  - ใช้ `_diff` อีกชุด (`sa_*` ใน manifest และ zip) ซึ่ง build จาก `backup/original/LocalData` ได้โดยไม่ต้องมีเกม standalone ในเครื่อง
  - ตั้งไฟล์ม็อดเป็น read-only เพราะ patcher ของเกมคอยเขียนคืน
  - เมื่อ `LocalData\Patch\patching_version.txt` เปลี่ยน play.bat จะคืนต้นฉบับให้เกมอัปเดตไฟล์ภาษาก่อน แล้วติดตั้งม็อดกลับในรอบถัดไป
  - รายละเอียดการทดสอบอยู่ใน [docs/OVERVIEW.md](docs/OVERVIEW.md)

ทดสอบโดยไม่แตะเกมจริงได้ด้วยตัวแปรสภาพแวดล้อม:

| ตัวแปร | ผล |
|---|---|
| `WWMTHAI_HOME` | ใช้โฟลเดอร์นี้แทน `%LOCALAPPDATA%\WWM-Thai` |
| `WWMTHAI_GAME` | ใช้โฟลเดอร์เกมนี้ (เช่นโฟลเดอร์จำลองที่ก๊อปไฟล์จาก `backup/original` ไปวาง) |
| `WWMTHAI_DESKTOP` | สร้าง shortcut ที่นี่แทน Desktop |
| `WWMTHAI_NOLAUNCH` | ไม่เปิดเกมจริง แค่บอกว่าจะเปิดอะไร |

## เอกสารอื่น

| ไฟล์ | เนื้อหา |
|---|---|
| [docs/OVERVIEW.md](docs/OVERVIEW.md) | ภาพรวมระบบทั้งหมด |
| [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) | กติกาภาษาและสำนวน |
| [docs/AGENT_TRANSLATION_GUIDE.md](docs/AGENT_TRANSLATION_GUIDE.md) | คู่มือสำหรับ AI ที่ช่วยแปล |
| [docs/AGENT_CHUNK_TASK.md](docs/AGENT_CHUNK_TASK.md) | การแบ่งงานแปลเป็นก้อน |
| [docs/HOW_TO_BUILD.md](docs/HOW_TO_BUILD.md) | ขั้นตอน build แบบละเอียด |
| [docs/MANUAL_INSTALL.md](docs/MANUAL_INSTALL.md) | ติดตั้งด้วยมือโดยไม่รันสคริปต์ (ผู้ใช้ขั้นสูง) |

เอกสารสำหรับผู้เล่นมี 2 ไฟล์ เนื้อหาเดียวกัน เขียนให้คนที่ไม่รู้เรื่องเทคนิคอ่านเข้าใจ:
[README.md](README.md) (หน้า GitHub) และ `release/README.txt` (อยู่ใน zip)
ถ้าแก้วิธีติดตั้งหรือข้อความในสคริปต์ ต้องแก้ทั้ง 2 ไฟล์ให้ตรงกัน
| [docs/EXTERNAL_AI_GUIDE.md](docs/EXTERNAL_AI_GUIDE.md) / [docs/CLAUDE_API_GUIDE.md](docs/CLAUDE_API_GUIDE.md) | ใช้ AI ภายนอก / Claude API ช่วยแปล |
| [docs/REVIEW_NOTES.md](docs/REVIEW_NOTES.md) | บันทึกการตรวจคำแปล |
