# ติดตั้งด้วยมือ (สำหรับผู้ใช้ขั้นสูง)

ผู้เล่นทั่วไปใช้ `install.bat` ตามวิธีใน [README.md](../README.md) ได้เลย ไม่ต้องอ่านหน้านี้

หน้านี้สำหรับคนที่ไม่อยากรันสคริปต์ใด ๆ ไฟล์ที่ต้องใช้อยู่ในโฟลเดอร์ `data` ของ zip
แต่ต้องเช็กเวอร์ชันและสำรองไฟล์เอง และไม่มีอัปเดตอัตโนมัติให้

1. **ปิดเกม**

2. **ไปที่โฟลเดอร์ไฟล์ภาษาของเกม**

   | แพลตฟอร์ม | โฟลเดอร์ | หาโฟลเดอร์เกมยังไง |
   |---|---|---|
   | Steam | `<คลังเกม Steam>\steamapps\common\Where Winds Meet\Package\HD\oversea\locale` | Steam > คลิกขวาที่เกม > Manage > Browse local files |
   | Launcher แบบ Lite | `<...>\wwm\wwm_lite\LocalData\Patch\HD\oversea\locale` | |
   | Launcher แบบ Standard ⚠️ | ยังไม่ได้ทดสอบ ไม่รู้ว่าไฟล์ภาษาอยู่ที่ไหนบ้าง (อาจอยู่ทั้งใน `Package\...` และ `LocalData\Patch\...`) | `<...>\wwm\wwm_standard` |

3. **เช็กว่าไฟล์ในเกมตรงกับม็อดเวอร์ชันนี้** (สำคัญที่สุด ห้ามข้าม)
   ไฟล์ม็อดที่ไม่ตรงกับไฟล์ในเกม จะทำให้ข้อความในเกมเพี้ยน

   **3.1 เช็กเร็ว (คัดออกอย่างเดียว)**
   - เปิด `data\manifest.txt` ดูบรรทัด `game_build=` (เช่น `2026-11-02/r64785`)
   - เปิด `<โฟลเดอร์เกม>\Engine\Binaries\Win64r\Built.version` ด้วย Notepad
   - ถ้าไม่ตรงกัน: หยุด ห้ามก๊อป ให้รอม็อดเวอร์ชันใหม่
   - ถ้าตรงกัน: ยังไม่พอ ต้องทำข้อ 3.2 ต่อ เพราะเกมแก้ไฟล์ภาษาทีหลังได้ (hot patch) โดยเลขนี้ไม่เปลี่ยน

   **3.2 เช็กจริง (SHA256)**
   - ในโฟลเดอร์จากข้อ 2 คลิกที่ช่อง address ด้านบนของหน้าต่าง พิมพ์ `cmd` แล้วกด Enter
   - พิมพ์ทีละบรรทัด
     ```
     certutil -hashfile translate_words_map_th SHA256
     certutil -hashfile translate_words_map_th_diff SHA256
     ```
   - ผลของแต่ละไฟล์ต้องตรงกับบรรทัดใน `data\manifest.txt` (ไม่สนตัวพิมพ์เล็ก/ใหญ่)
     - Steam: `orig_translate_words_map_th=...` และ `orig_translate_words_map_th_diff=...`
     - Launcher: `sa_orig_translate_words_map_th=...` และ `sa_orig_translate_words_map_th_diff=...`
   - ถ้าไฟล์ไหนไม่ตรง: หยุด ห้ามก๊อป
     (ถ้าตรงกับ `mod_...` / `sa_mod_...` แทน แปลว่าลงม็อดเวอร์ชันนี้ไว้แล้ว ไม่ต้องทำอะไร)

4. **สำรองไฟล์ 2 ไฟล์นี้ไปเก็บไว้ที่อื่น:** `translate_words_map_th` และ `translate_words_map_th_diff`

5. **ก๊อปไฟล์จาก `data` ของ zip ไปวางทับ**
   - Steam: `translate_words_map_th` และ `translate_words_map_th_diff`
   - Launcher: `translate_words_map_th` และ `sa_translate_words_map_th_diff`
     - เปลี่ยนชื่อตัวหลังเป็น `translate_words_map_th_diff` หลังวาง
     - คลิกขวาทั้ง 2 ไฟล์ > Properties > ติ๊ก **Read-only** > OK
       (ถ้าไม่ติ๊ก Launcher จะเขียนกลับเป็นภาษาไทยเดิมตอนเปิดเกม)

6. **เข้าเกม** ตั้งภาษาเป็นภาษาไทย แล้วเปิดแผนที่ ดูภูเขายอดฮิต ต้องขึ้นว่า "เขาปู้เจี้ยน"

**เมื่อเกมอัปเดต:** ตัวอัปเดตเกมจะเขียนทับไฟล์ กลับเป็นภาษาไทยเดิม
ให้รอม็อดเวอร์ชันใหม่ แล้วทำข้อ 1–6 ใหม่ (อย่าก๊อปไฟล์ม็อดเก่าทับเกมใหม่)
Launcher: เอาติ๊ก Read-only ออกก่อนให้เกมอัปเดต ไม่งั้นเกมจะอัปเดตไฟล์ภาษาไม่ได้

**ถอนการติดตั้ง:** ก๊อปไฟล์ที่สำรองไว้กลับไปวาง หรือใช้ปุ่มซ่อมไฟล์เกม
(Launcher: เอาติ๊ก Read-only ของ 2 ไฟล์ออกก่อน)

- Steam: คลิกขวาที่เกม > Properties > Installed Files > Verify integrity of game files
- Launcher: ปุ่มตรวจสอบ/ซ่อมไฟล์ใน Launcher
