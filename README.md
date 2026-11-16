# Where Winds Meet: แปลไทยใหม่ทั้งเกม

ม็อดแฟนเมดที่แปลภาษาไทยของ Where Winds Meet ใหม่ทั้งหมดจากต้นฉบับภาษาจีน
(~480,000 ข้อความ) ให้อ่านลื่นและเรียกชื่อเฉพาะสม่ำเสมอทั้งเกม
ไม่ใช่ของทางการ และไม่เกี่ยวข้องกับ NetEase / Everstone Studio

## สำหรับผู้เล่น

โหลด zip ล่าสุดจากหน้า **Releases** แตกไฟล์ แล้วดับเบิลคลิก `install.bat`
วิธีใช้ทั้งหมดอยู่ใน [release/README.txt](release/README.txt)

## สำหรับนักพัฒนา

ภาพรวมทั้งระบบ (เกมเก็บข้อความยังไง, ไปป์ไลน์การแปล, การ build/อัปเดต): [docs/OVERVIEW.md](docs/OVERVIEW.md)

| โฟลเดอร์ | เนื้อหา |
|---|---|
| `translations/` | คำแปลทั้งหมด `zh<TAB>th` แยกตามประเภท (ส่ง PR แก้คำแปลได้ที่นี่) |
| `glossary/` | ชื่อเฉพาะ (`series_names.tsv`) และศัพท์ (`glossary.tsv`) |
| `tools/` | สคริปต์ Python: อ่าน/เขียนไฟล์ภาษาของเกม, ฐานข้อมูล, ตรวจคำแปล, ทำ release |
| `docs/` | คู่มือภาษา/การแปล/การ build |
| `release/` | ชุดติดตั้งสำหรับผู้เล่น (`.bat` + PowerShell) |

### เริ่มทำงานบนเครื่องใหม่ (clone ครั้งแรก / ล้างเครื่อง)

ต้องมี: ตัวเกม (ภาษาไทยต้นฉบับ **ไม่ได้ลงม็อดอยู่**: ถ้าลงอยู่ ให้ Steam > Verify integrity ก่อน)
และ Python 3.10+ (ติ๊ก "Add python.exe to PATH" ตอนติดตั้ง)

```
git clone https://github.com/poomsakk/wwm-thai-localization-enhanced.git
```

แล้วดับเบิลคลิก **`setup.bat`** ครั้งเดียว มันจะ: ลงไลบรารี Python → หาโฟลเดอร์เกมจาก Steam (บันทึกใน `local.cfg`)
→ สำรองไฟล์ไทยต้นฉบับไว้ใน `backup\original` → สร้าง `work\wwm.db` → โหลดคำแปลทั้งหมดจาก `translations/`
ไฟล์เกมต้นฉบับ (`backup/`) และฐานข้อมูล (`work/`) ไม่อยู่ใน repo เพราะใหญ่และเป็นข้อมูลของเกม

### งานประจำ

| งาน | วิธี |
|---|---|
| build + ติดตั้งม็อดลงเกม | `build_mod.bat` (ดึงคำแปลที่เปลี่ยนใน git เข้า DB ก่อน แล้ว export `translations/` ให้เอง) |
| เกมอัปเดต | `update_game.bat` → แปลข้อความใหม่ (`translate.py chunks --new`) → `build_mod.bat` |
| เพิ่ม/แก้ชื่อเฉพาะ | แก้ `glossary/series_names.tsv` → `python -I tools/name_pass.py --apply` → `build_mod.bat` |
| แจกงานให้ subagent หลายตัว | `python -I tools/next_chunk.py [ก้อนที่เสร็จ]` (ดู docs/AGENT_CHUNK_TASK.md) |
| ออก release | `build_mod.bat` → `python -I tools/make_release.py` → อัปโหลด `dist/<version>/*.zip` และ `manifest.txt` ขึ้น GitHub Release |
| เก็บงานขึ้น GitHub | `git add -A` → `git commit -m "..."` → `git push` |

### ส่งคำแปลมาช่วย (contributor)

แก้บรรทัดใน `translations/<ประเภท>.tsv` (คอลัมน์ `th`; ห้ามแตะคอลัมน์ `zh`) แล้วเปิด Pull Request
ต้องคงรหัสพิเศษ (`#Y…#E`, `{0}`, `%s`, `\n`, `<LINK…>`) ให้เหมือนต้นฉบับ และใช้ชื่อตาม `glossary/series_names.tsv`
กติกาภาษาอยู่ใน [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md)
