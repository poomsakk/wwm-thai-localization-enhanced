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

ไฟล์เกมต้นฉบับ (`backup/`) และฐานข้อมูล (`work/`) ไม่อยู่ใน repo เพราะใหญ่และเป็นข้อมูลของเกม
สร้างขึ้นใหม่ได้จากเกมที่ติดตั้งในเครื่อง (เกมต้องเป็นไฟล์ไทยต้นฉบับ ไม่ได้ลงม็อดอยู่):
ก๊อป `translate_words_map_*` จาก `<เกม>\Package\HD\oversea\locale` ไปไว้ใน `backup\original\Package\`
(และจาก `LocalData\Patch\HD\oversea\locale` ไปไว้ใน `backup\original\LocalData\`) แล้ว

```
python -I tools/build_db.py
python -I tools/export_translations.py import
build_mod.bat
```

ออก release: `build_mod.bat` แล้ว `python -I tools/make_release.py`
จากนั้นอัปโหลดทั้ง `dist/<version>/*.zip` และ `dist/<version>/manifest.txt` ขึ้น GitHub Release
