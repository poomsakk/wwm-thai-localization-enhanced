# =====================================================================
#  ม็อดแปลไทย Where Winds Meet — ตัวติดตั้ง / อัปเดต / ถอนการติดตั้ง
#
#  ทำงานด้วย Windows PowerShell ที่มากับ Windows (ไม่ต้องลงโปรแกรมเพิ่ม)
#  ถูกเรียกจาก install.bat / play.bat / uninstall.bat
#
#  ไฟล์ในเกมที่สคริปต์นี้แก้ไข มีแค่ 2 ไฟล์:
#    <โฟลเดอร์เกม>\Package\HD\oversea\locale\translate_words_map_th          (Steam)
#    <โฟลเดอร์เกม>\Package\HD\oversea\locale\translate_words_map_th_diff
#  Launcher ของเกม (standalone) ใช้ LocalData\Patch\HD\oversea\locale แทน
#  และตั้งไฟล์ม็อดเป็น read-only เพราะ launcher คอยเขียนไฟล์ในโฟลเดอร์นั้นคืน
#
#  กติกาความปลอดภัย:
#   - ก่อนแก้ไฟล์ จะสำรองต้นฉบับไว้ที่ %LOCALAPPDATA%\WWM-Thai\games\<เกม>\backup เสมอ
#   - มีหลายเกมในเครื่อง (เช่น Steam + Launcher) ได้: แต่ละเกมมีข้อมูล/ไฟล์สำรองของตัวเอง
#   - จะวางไฟล์ม็อดก็ต่อเมื่อไฟล์ในเกมตรงกับเวอร์ชันที่ม็อดสร้างมา (เช็ก SHA256)
#     ถ้าเกมอัปเดตแล้วไม่ตรง จะไม่แตะอะไรเลย (กันข้อความในเกมเพี้ยน)
#   - อัปเดตอัตโนมัติจะโหลดจาก GitHub Releases ของ $Repo เท่านั้น
#     ตรวจ SHA256 ก่อนใช้ และแทนที่เฉพาะ "ไฟล์ข้อมูลภาษา" — ไม่เคยแทนที่สคริปต์
# =====================================================================
param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'play', 'uninstall')][string]$Mode,
    [string]$GameExe = '',
    [string]$Game = ''
)
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

# ---------------- ตั้งค่า ----------------
$Repo            = ''   # GitHub "owner/repo" สำหรับอัปเดตอัตโนมัติ (ว่าง = ไม่เช็กออนไลน์) — make_release ใส่ให้
$Files           = @('translate_words_map_th', 'translate_words_map_th_diff')
# ที่เก็บไฟล์ภาษา: Steam ใช้ Package\HD, ตัวติดตั้งของเกมเอง (standalone) ใช้ LocalData\Patch\HD
$LocaleRels      = @('Package\HD\oversea\locale', 'LocalData\Patch\HD\oversea\locale')
$SteamAppId      = '3564740'
$ShortcutName    = 'Where Winds Meet (Thai).lnk'   # WScript.Shell บันทึกชื่อไฟล์ภาษาไทยไม่ได้

$ModHome   = if ($env:WWMTHAI_HOME) { $env:WWMTHAI_HOME } else { Join-Path $env:LOCALAPPDATA 'WWM-Thai' }
$LogFile   = Join-Path $ModHome 'log.txt'
$GamesDir  = Join-Path $ModHome 'games'   # ข้อมูลแยกต่อเกม: games\<เกม>\data (คำแปล), backup (ต้นฉบับ), state.txt
# ค่าด้านล่างถูกตั้งใหม่ด้วย Set-Game ทุกครั้งก่อนทำงานกับเกมไหน
$DataDir   = Join-Path $ModHome 'data'
$BackupDir = Join-Path $ModHome 'backup'
$StateFile = Join-Path $ModHome 'state.txt'
$script:ProfileDir = $ModHome
New-Item -ItemType Directory -Force -Path $ModHome | Out-Null
$script:ExitCode = 0

# ---------------- เครื่องมือเล็ก ๆ ----------------
function Log([string]$m) {
    try {
        if ((Test-Path -LiteralPath $LogFile) -and (Get-Item -LiteralPath $LogFile).Length -gt 1MB) { Remove-Item -LiteralPath $LogFile }
        Add-Content -LiteralPath $LogFile -Value ('{0:yyyy-MM-dd HH:mm:ss} [{1}] {2}' -f (Get-Date), $Mode, $m) -Encoding UTF8
    } catch {}
}
function Say([string]$m, [string]$color = 'Gray') { Write-Host $m -ForegroundColor $color; Log $m }

# อ่าน/เขียนไฟล์ข้อความแบบ key=value
function Read-KV([string]$path) {
    $kv = @{}
    if ($path -and (Test-Path -LiteralPath $path)) {
        foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8) {
            $i = $line.IndexOf('=')
            if ($i -gt 0) { $kv[$line.Substring(0, $i).Trim()] = $line.Substring($i + 1).Trim() }
        }
    }
    return $kv
}
function Write-KV([string]$path, [hashtable]$kv) {
    $kv.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" } |
        Set-Content -LiteralPath $path -Encoding UTF8
}
function Hash([string]$path) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return '' }
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
}
# โฟลเดอร์ไฟล์ภาษาของเกมนี้ (ที่มีไฟล์ไทยหลักอยู่จริง) หรือ $null
function Get-LocaleDir([string]$game) {
    if (-not $game) { return $null }
    foreach ($rel in $LocaleRels) {
        $d = Join-Path $game $rel
        if (Test-Path -LiteralPath (Join-Path $d $Files[0])) { return $d }
    }
    return $null
}
function GameFile([string]$game, [string]$f) {
    $d = Get-LocaleDir $game
    if (-not $d) { $d = Join-Path $game $LocaleRels[0] }
    return Join-Path $d $f
}
function Test-Game([string]$dir) { return [bool](Get-LocaleDir $dir) }
# launcher.exe ของตัวติดตั้งเกม: <wwm>\Win32\deploy\launcher.exe (โฟลเดอร์เกมคือ <wwm>\wwm_lite หรือ wwm_standard)
function Get-Launcher([string]$game) {
    $root = Split-Path $game
    @((Join-Path $root 'Win32\deploy\launcher.exe'), (Join-Path $root 'launcher.exe'), (Join-Path $game 'launcher.exe')) |
        Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
function Test-GameRunning { return [bool](Get-Process -Name 'wwm' -ErrorAction SilentlyContinue) }

# ---------------- ตัวติดตั้งของเกม (standalone) ----------------
# ไฟล์ภาษาอยู่ใน LocalData\Patch ซึ่ง launcher/patcher ของเกมคอยเขียนคืน:
#  - _diff ของ standalone คนละไฟล์กับของ Steam -> manifest มีค่า sa_orig_* / sa_mod_* และไฟล์ data\sa_*
#  - ไฟล์ม็อดถูกตั้งเป็น read-only (patcher เขียนทับไม่ได้ จะข้ามไปเงียบ ๆ)
#  - เกมอัปเดต (patching_version.txt เปลี่ยน) -> คืนต้นฉบับให้ patcher อัปเดตไฟล์ภาษาได้ แล้วค่อยติดตั้งใหม่
$script:SA = $false
function Set-Variant([string]$game) { $script:SA = [bool]($game -and ((Get-LocaleDir $game) -like '*\LocalData\*')) }
# manifest ในมุมของเกมนี้: บน standalone ใช้ค่า sa_* แทน orig_* / mod_* และบอกชื่อไฟล์ข้อมูล (src_*)
function Get-ModMan([hashtable]$m) {
    $r = @{}; foreach ($k in $m.Keys) { $r[$k] = $m[$k] }
    if ($m.ContainsKey('_variant')) { return $r }
    $r['_variant'] = 'pkg'
    if ($script:SA -and $m.ContainsKey("sa_orig_$($Files[0])")) {
        $r['_variant'] = 'sa'
        foreach ($f in $Files) {
            $r["orig_$f"] = $m["sa_orig_$f"]; $r["mod_$f"] = $m["sa_mod_$f"]
            if ($m["sa_mod_$f"] -ne $m["mod_$f"]) { $r["src_$f"] = "sa_$f" }
        }
    }
    return $r
}
function Src([hashtable]$man, [string]$f) { if ($man["src_$f"]) { return $man["src_$f"] } else { return $f } }
function Set-RO([string]$path, [bool]$on) {
    if (Test-Path -LiteralPath $path -PathType Leaf) { (Get-Item -LiteralPath $path).IsReadOnly = $on }
}
function Get-PatchVer([string]$game) {
    $p = Join-Path $game 'LocalData\Patch\patching_version.txt'
    if (Test-Path -LiteralPath $p) { return ([string](Get-Content -LiteralPath $p -Raw)).Trim() } else { return '' }
}

# ---------------- หลายเกมในเครื่องเดียว ----------------
function Norm-Path([string]$p) {
    if (-not $p) { return '' }
    $p = $p.Trim().Trim('"')
    try { $p = [IO.Path]::GetFullPath($p) } catch {}
    return $p.TrimEnd('\')
}
# ชื่อโฟลเดอร์ข้อมูลของเกม เช่น steam-1a2b3c4d, wwm_lite-5e6f7a8b (จากที่อยู่เกม)
function Get-GameKey([string]$game) {
    $p = (Norm-Path $game).ToLower()
    $sha = [Security.Cryptography.SHA1]::Create()
    $h = -join ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($p))[0..3] | ForEach-Object { $_.ToString('x2') })
    $leaf = Split-Path $p -Leaf
    $kind = if ($p -match '\\steamapps\\common\\') { 'steam' } elseif ($leaf -match '^wwm_(standard|lite)$') { $leaf } else { 'game' }
    return "$kind-$h"
}
# ตั้งที่เก็บข้อมูล (data / backup / state.txt) ให้เป็นของเกมนี้
function Set-Game([string]$game) {
    $script:ProfileDir = Join-Path $GamesDir (Get-GameKey $game)
    $script:DataDir    = Join-Path $script:ProfileDir 'data'
    $script:BackupDir  = Join-Path $script:ProfileDir 'backup'
    $script:StateFile  = Join-Path $script:ProfileDir 'state.txt'
    Set-Variant $game
}
# เกมที่ลงม็อดไว้ (มีโฟลเดอร์ข้อมูลใน games\)
function Get-ModGames {
    if (-not (Test-Path -LiteralPath $GamesDir)) { return }
    foreach ($d in Get-ChildItem -LiteralPath $GamesDir -Directory) {
        $g = (Read-KV (Join-Path $d.FullName 'state.txt'))['game_path']
        if ($g) { Norm-Path $g }
    }
}
# ม็อดเวอร์ชันก่อน ๆ เก็บ data / backup / state.txt ไว้ชุดเดียว: ย้ายไปเป็นของเกมที่ลงไว้
function Move-Legacy {
    $old = Join-Path $ModHome 'state.txt'
    $names = @('data', 'backup', 'state.txt') | Where-Object { Test-Path -LiteralPath (Join-Path $ModHome $_) }
    if (-not $names) { return }
    $g = (Read-KV $old)['game_path']
    if (-not $g) { Log 'legacy data without game_path: left as is'; return }
    $d = Join-Path $GamesDir (Get-GameKey $g)
    if (Test-Path -LiteralPath (Join-Path $d 'state.txt')) { Log "legacy data: $d already exists, left as is"; return }
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    foreach ($n in $names) { Move-Item -LiteralPath (Join-Path $ModHome $n) -Destination (Join-Path $d $n) -Force }
    Log "moved legacy data ($($names -join ', ')) to $d"
}
function Ask([string]$prompt) {
    if ($env:WWMTHAI_ANSWER) { Say "$prompt $env:WWMTHAI_ANSWER"; return $env:WWMTHAI_ANSWER }   # สำหรับทดสอบ
    return Read-Host $prompt
}

# ---------------- หาโฟลเดอร์เกม (Steam / ตัวติดตั้งของเกม) ----------------
# แปลงสิ่งที่ผู้ใช้ให้มา (โฟลเดอร์เกม, wwm.exe, launcher.exe หรือโฟลเดอร์ wwm ที่มี wwm_standard) เป็นโฟลเดอร์เกม
function Resolve-GameDir([string]$p) {
    if (-not $p) { return $null }
    $p = $p.Trim().Trim('"')
    if (Test-Path -LiteralPath $p -PathType Leaf) {
        if ((Split-Path $p -Leaf) -ieq 'wwm.exe') { for ($i = 0; $i -lt 4; $i++) { $p = Split-Path $p } }
        else { $p = Split-Path $p }   # เช่น launcher.exe ของตัวติดตั้งเกม
    }
    foreach ($c in @($p, (Join-Path $p 'wwm_standard'), (Join-Path $p 'wwm_lite'))) {
        if (Test-Game $c) { return (Norm-Path $c) }
    }
    return $null
}
function Get-SteamGames {
    $libs = @()
    try {
        $steam = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -Name SteamPath).SteamPath -replace '/', '\'
        $libs += $steam
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($m in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw -Encoding UTF8), '"path"\s+"([^"]+)"')) {
                $libs += ($m.Groups[1].Value -replace '\\\\', '\')
            }
        }
    } catch {}
    foreach ($lib in $libs) { Resolve-GameDir (Join-Path $lib 'steamapps\common\Where Winds Meet') }
}
function Get-StandaloneGames {
    # จากรายการโปรแกรมที่ติดตั้ง (Add/Remove Programs)
    $keys = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
            'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    foreach ($k in $keys) {
        Get-ItemProperty -Path $k -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -match 'Where Winds Meet|燕云十六声' -and $_.InstallLocation } |
            ForEach-Object { Resolve-GameDir $_.InstallLocation }
    }
    # ที่ติดตั้งยอดนิยม
    foreach ($drive in 'C', 'D', 'E', 'F') {
        foreach ($rel in 'Program Files\wwm', 'Program Files (x86)\wwm', 'Games\wwm', 'wwm') {
            $p = "${drive}:\$rel"
            if (Test-Path -LiteralPath $p) { Resolve-GameDir $p }
        }
    }
}
function Find-AllGames {
    $seen = @{}
    $found = @(if ($env:WWMTHAI_GAME) { $env:WWMTHAI_GAME -split ';' | ForEach-Object { Resolve-GameDir $_ } }   # สำหรับทดสอบ
               else { Get-SteamGames; Get-StandaloneGames })
    foreach ($g in $found + @(Get-ModGames | Where-Object { Test-Game $_ })) {
        if ($g -and -not $seen.ContainsKey($g.ToLower())) { $seen[$g.ToLower()] = $true; $g }
    }
}
function Get-Platform([string]$game) {
    if ($game -match '\\steamapps\\common\\') { return 'steam' }
    if ((Split-Path $game -Leaf) -match '^wwm_(standard|lite)$' -or (Get-LocaleDir $game) -like '*\LocalData\*') { return 'standalone' }
    return 'other'
}
# เลือกเกมที่จะติดตั้ง (หรือถอนการติดตั้งถ้า -Installed): คืนรายการโฟลเดอร์เกม (ว่าง = ยกเลิก)
function Select-Games([switch]$Installed) {
    $all = @(if ($Installed) { Get-ModGames } else { Find-AllGames })
    if ($all.Count -eq 1) { return $all[0] }
    if ($all.Count -gt 1) {
        $mod = @(Get-ModGames)
        Say 'พบเกมมากกว่าหนึ่งที่:' 'Yellow'
        for ($i = 0; $i -lt $all.Count; $i++) {
            $tag = if (-not $Installed -and $mod -contains $all[$i]) { '  - ลงม็อดไว้แล้ว' } else { '' }
            Say ("  [{0}] {1}  ({2}){3}" -f ($i + 1), $all[$i], (Get-Platform $all[$i]), $tag)
        }
        Say '  [A] ทุกเกมข้างบน'
        while ($true) {
            $n = ([string](Ask 'เลือกหมายเลข หรือ A (กด Enter เปล่า ๆ = ยกเลิก)')).Trim()
            if (-not $n) { return }
            if ($n -ieq 'a') { return $all }
            if ($n -match '^\d+$' -and [int]$n -ge 1 -and [int]$n -le $all.Count) { return $all[[int]$n - 1] }
            Say 'ไม่มีหมายเลขนี้' 'Red'
            if ($env:WWMTHAI_ANSWER) { return }
        }
    }
    if ($Installed) { return }
    while ($true) {
        Say 'หาโฟลเดอร์เกมไม่เจอ: ลากโฟลเดอร์เกม (หรือไฟล์ wwm.exe / launcher.exe) มาวางในหน้าต่างนี้ แล้วกด Enter (กด Enter เปล่า ๆ = ยกเลิก)' 'Yellow'
        $p = Read-Host 'โฟลเดอร์เกม'
        if (-not $p.Trim()) { return }
        $g = Resolve-GameDir $p
        if ($g) { return $g }
        Say "ไม่พบไฟล์ภาษาของเกมใน: $p" 'Red'
    }
}
# เกมของ shortcut ที่ไม่ได้ระบุเกม (shortcut จากม็อดเวอร์ชันก่อน): เกมที่ลงม็อดไว้ เน้น Launcher ก่อน
function Find-PlayGame {
    $mod = @(Get-ModGames | Where-Object { Test-Game $_ })
    $sa = @($mod | Where-Object { (Get-Platform $_) -ne 'steam' })
    if ($sa.Count) { return $sa[0] }
    if ($mod.Count) { return $mod[0] }
    return @(Find-AllGames)[0]
}

# ---------------- เปิดเกม (สำหรับ shortcut ของตัวติดตั้งเกม) ----------------
function Start-Game([string]$game) {
    $platform = Get-Platform $game
    $target = switch ($platform) {
        'steam' { "steam://rungameid/$SteamAppId" }
        default {
            # ตัวติดตั้งของเกม: เปิดผ่าน launcher.exe (อัปเดตเกมให้ก่อน) ถ้ามี ไม่งั้นเปิด wwm.exe ตรง ๆ
            $l = Get-Launcher $game
            if ($l) { $l } else { Join-Path $game 'Engine\Binaries\Win64r\wwm.exe' }
        }
    }
    Log "launch ($platform): $target"
    if ($env:WWMTHAI_NOLAUNCH) { Say "(ทดสอบ) จะเปิด: $target"; return }
    Start-Process -FilePath $target
}
function Get-Desktop {
    if ($env:WWMTHAI_DESKTOP) { return $env:WWMTHAI_DESKTOP }   # override สำหรับทดสอบ
    return [Environment]::GetFolderPath('Desktop')
}
# shortcut ของม็อดบน Desktop: @{ Path; Game } (Game ว่าง = shortcut จากม็อดเวอร์ชันก่อน ไม่ได้ระบุเกม)
function Get-PlayShortcuts {
    $desk = Get-Desktop
    if (-not (Test-Path -LiteralPath $desk)) { return }
    $ws = New-Object -ComObject WScript.Shell
    $bat = Join-Path $ModHome 'play.bat'
    foreach ($f in Get-ChildItem -LiteralPath $desk -Filter 'Where Winds Meet (Thai)*.lnk' -File) {
        $s = $ws.CreateShortcut($f.FullName)
        if ($s.TargetPath -ne $bat) { continue }
        $g = if ($s.Arguments -match '--game\s+"([^"]+)"') { Norm-Path $Matches[1] } else { '' }
        @{ Path = $f.FullName; Game = $g }
    }
}
function New-PlayShortcut([string]$game) {
    $desk = Get-Desktop
    $mine = @(Get-PlayShortcuts | Where-Object { $_.Game -eq $game -or -not $_.Game })
    if ($mine.Count) { $lnk = $mine[0].Path }
    else {
        $lnk = Join-Path $desk $ShortcutName
        if (Test-Path -LiteralPath $lnk) { $lnk = Join-Path $desk ('Where Winds Meet (Thai) - ' + (Split-Path $game -Leaf) + '.lnk') }
    }
    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($lnk)
    $s.TargetPath = Join-Path $ModHome 'play.bat'
    $s.Arguments = "--game `"$game`""
    $s.WorkingDirectory = $ModHome
    $s.WindowStyle = 7   # เปิดหน้าต่างแบบย่อ
    $s.Description = 'Check the Thai mod, then start Where Winds Meet'
    $s.Save()
    return $lnk
}

# ---------------- สถานะไฟล์ในเกม ----------------
# แต่ละไฟล์เป็น 'mod' (ของม็อดชุดนี้), 'orig' (ต้นฉบับที่ม็อดชุดนี้รองรับ) หรือ 'other'
function Get-Status([string]$game, [hashtable]$man) {
    $states = foreach ($f in $Files) {
        $h = Hash (GameFile $game $f)
        if (-not $h) { 'other' } elseif ($h -eq $man["mod_$f"]) { 'mod' } elseif ($h -eq $man["orig_$f"]) { 'orig' } else { 'other' }
    }
    if ($states -contains 'other') { return 'other' }
    if ($states -contains 'orig') { return 'orig' }
    return 'mod'
}
# hash ของ "ต้นฉบับ" ในเกมตอนนี้ (ถ้าไฟล์เป็นของม็อดอยู่ ใช้ค่าต้นฉบับจาก manifest แทน)
function Get-GameOrig([string]$game, [hashtable]$man) {
    $o = @{}
    foreach ($f in $Files) {
        $h = Hash (GameFile $game $f)
        $o[$f] = if ($h -and $h -eq $man["mod_$f"]) { $man["orig_$f"] } else { $h }
    }
    return $o
}
function Test-Compatible([hashtable]$orig, [hashtable]$man) {
    foreach ($f in $Files) { if (-not $man["orig_$f"] -or $orig[$f] -ne $man["orig_$f"]) { return $false } }
    return $true
}

# ---------------- ติดตั้ง / คืนไฟล์ ----------------
function Install-Data([string]$game, [hashtable]$man, [string]$dataDir) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    foreach ($f in $Files) {
        $dst = GameFile $game $f
        $h = Hash $dst
        if ($h -eq $man["mod_$f"]) { if ($script:SA) { Set-RO $dst $true }; continue }
        if ($h -ne $man["orig_$f"]) { throw "ไฟล์ $f ในเกมไม่ตรงกับเวอร์ชันที่ม็อดรองรับ" }
        $bak = Join-Path $BackupDir $f
        if ((Hash $bak) -ne $h) {
            Copy-Item -LiteralPath $dst -Destination $bak -Force
            if ((Hash $bak) -ne $h) { throw "สำรองไฟล์ $f ไม่สำเร็จ" }
        }
        Set-RO $dst $false
        Copy-Item -LiteralPath (Join-Path $dataDir (Src $man $f)) -Destination $dst -Force
        if ((Hash $dst) -ne $man["mod_$f"]) {
            Copy-Item -LiteralPath $bak -Destination $dst -Force
            throw "คัดลอกไฟล์ $f ไม่สำเร็จ (คืนไฟล์เดิมให้แล้ว)"
        }
        if ($script:SA) { Set-RO $dst $true }
    }
}
# คืนต้นฉบับให้ทุกไฟล์ที่เป็นของม็อดชุด $man อยู่ — คืน $false ถ้ามีไฟล์ที่คืนไม่ได้
function Restore-Original([string]$game, [hashtable]$man) {
    $ok = $true
    foreach ($f in $Files) {
        $dst = GameFile $game $f
        if (-not $man["mod_$f"] -or (Hash $dst) -ne $man["mod_$f"]) { continue }
        $bak = Join-Path $BackupDir $f
        if ((Hash $bak) -eq $man["orig_$f"]) {
            Set-RO $dst $false
            Copy-Item -LiteralPath $bak -Destination $dst -Force
            if ((Hash $dst) -eq $man["orig_$f"]) { continue }
        }
        Say "คืนไฟล์ต้นฉบับ $f ไม่ได้" 'Red'
        $ok = $false
    }
    return $ok
}
# สลับไปใช้ข้อมูลชุดใหม่: คืนต้นฉบับของชุดเก่า -> คัดลอกข้อมูลชุดใหม่ -> ติดตั้ง
function Use-Kit([string]$game, [hashtable]$oldMan, [string]$newDataDir) {
    $newMan = Get-ModMan (Read-KV (Join-Path $newDataDir 'manifest.txt'))
    if (-not (Restore-Original $game $oldMan)) { throw 'คืนไฟล์ต้นฉบับก่อนเปลี่ยนเวอร์ชันไม่สำเร็จ' }
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    Get-ChildItem -LiteralPath $DataDir -File | Remove-Item -Force   # ไฟล์ของชุดเก่า (เช่น sa_*) ไม่ค้าง
    foreach ($it in Get-ChildItem -LiteralPath $newDataDir -File) {
        Copy-Item -LiteralPath $it.FullName -Destination (Join-Path $DataDir $it.Name) -Force
    }
    Install-Data $game $newMan $DataDir
    return $newMan
}

# ---------------- อัปเดตออนไลน์ (GitHub Releases) ----------------
function Get-Web([string]$url, [string]$outFile = '', [int]$timeout = 15) {
    $p = @{ Uri = $url; UseBasicParsing = $true; TimeoutSec = $timeout; Headers = @{ 'User-Agent' = 'wwm-thai-mod' } }
    if ($outFile) { $p.OutFile = $outFile; $p.TimeoutSec = 900 }
    return Invoke-WebRequest @p
}
# เลขเวอร์ชันจากชื่อ tag เช่น v2026.11.17 -> 2026.11.17 (อ่านไม่ได้ = $null)
function Tag-Version([string]$tag) {
    try { return [version]($tag -replace '^[vV]', '') } catch { return $null }
}
# หา release ใหม่สุดที่สร้างจากต้นฉบับ $orig และเวอร์ชันใหม่กว่า $minVersion
# ปกติใช้แค่ 1 request (รายการ release) — โหลด manifest เฉพาะ release ที่ tag ใหม่กว่าเท่านั้น
function Find-Update([hashtable]$orig, [version]$minVersion) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $prefix = "https://github.com/$Repo/releases/download/"
    $rels = @((Get-Web "https://api.github.com/repos/$Repo/releases?per_page=30" -timeout 6).Content | ConvertFrom-Json) |
        ForEach-Object { $_ } |
        Where-Object { -not $_.draft -and -not $_.prerelease } |
        Sort-Object -Descending -Property @{ Expression = { $v = Tag-Version $_.tag_name; if ($v) { $v } else { [version]'0.0' } } }
    foreach ($r in $rels) {
        $tv = Tag-Version $r.tag_name
        if ($tv -and $tv -le $minVersion) { break }   # เรียงใหม่ไปเก่า: ที่เหลือเก่ากว่าทั้งหมด
        $ma = $r.assets | Where-Object { $_.name -eq 'manifest.txt' } | Select-Object -First 1
        if (-not $ma -or -not $ma.browser_download_url.StartsWith($prefix)) { continue }
        $tmp = [IO.Path]::GetTempFileName()
        try { Get-Web $ma.browser_download_url $tmp | Out-Null; $m = Get-ModMan (Read-KV $tmp) } finally { Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue }
        if (-not (Test-Compatible $orig $m)) { continue }
        try { $v = [version]$m['mod_version'] } catch { continue }
        if ($v -le $minVersion) { continue }
        $za = $r.assets | Where-Object { $_.name -eq $m['zip_name'] } | Select-Object -First 1
        if (-not $za -or -not $za.browser_download_url.StartsWith($prefix)) { continue }
        return @{ Version = $v; Man = $m; Url = $za.browser_download_url }   # ใหม่สุดที่เข้ากับเกม
    }
    return $null
}
# ดาวน์โหลด + ตรวจ แล้วคืนโฟลเดอร์ data ที่ตรวจแล้ว (อยู่ใน $tmp)
$script:Fetched = @{}   # url -> โฟลเดอร์ data ที่โหลดแล้วในรอบนี้ (ลงหลายเกมไม่ต้องโหลดซ้ำ)
function Get-Update($u, [string]$tmp) {
    $dir = $script:Fetched[$u.Url]
    if (-not $dir -or -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $tmp | Out-Null
        $n = $script:Fetched.Count
        $zip = Join-Path $tmp "mod$n.zip"
        Say "กำลังดาวน์โหลดม็อดเวอร์ชัน $($u.Version) ..." 'Cyan'
        Get-Web $u.Url $zip | Out-Null
        if ((Hash $zip) -ne $u.Man['zip_sha256']) { throw 'ไฟล์ที่ดาวน์โหลดไม่ตรงกับ SHA256 ที่ประกาศไว้' }
        Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $tmp "x$n")
        $inner = Get-ChildItem -LiteralPath (Join-Path $tmp "x$n") -Recurse -Filter 'manifest.txt' |
            Where-Object { $_.Directory.Name -eq 'data' } | Select-Object -First 1
        if (-not $inner) { throw 'ไม่พบข้อมูลภาษาในไฟล์ที่ดาวน์โหลด' }
        $dir = $inner.DirectoryName
        $script:Fetched[$u.Url] = $dir
    }
    $m = Get-ModMan (Read-KV (Join-Path $dir 'manifest.txt'))
    foreach ($f in $Files) {
        if ($m["mod_$f"] -ne $u.Man["mod_$f"] -or (Hash (Join-Path $dir (Src $m $f))) -ne $m["mod_$f"]) {
            throw "ไฟล์ $f ในชุดอัปเดตไม่ถูกต้อง"
        }
    }
    return $dir
}

# ---------------- โหมดต่าง ๆ ----------------
function Show-LaunchOption {
    $line = '"' + (Join-Path $ModHome 'play.bat') + '" %command%'
    try { Set-Clipboard -Value $line } catch {}
    Say ''
    Say 'อยากให้ม็อดอัปเดตเองทุกครั้งที่กด Play (แนะนำ):' 'Cyan'
    Say '  Steam > คลิกขวาที่เกม > Properties > General > Launch Options แล้ววางบรรทัดนี้ (ก๊อปไว้ให้แล้ว กด Ctrl+V):'
    Say "  $line" 'White'
}
# ตัวติดตั้งของเกม ใส่คำสั่งก่อนเปิดเกมไม่ได้ จึงให้เปิดเกมผ่าน shortcut บน Desktop แทน
function Show-PlayShortcut([string]$game) {
    Say ''
    try {
        $lnk = New-PlayShortcut $game
        Say 'อยากให้ม็อดอัปเดตเองทุกครั้งที่เล่น (แนะนำ):' 'Cyan'
        Say "  เปิดเกมจาก shortcut บน Desktop: $([IO.Path]::GetFileNameWithoutExtension($lnk))" 'White'
        $how = 'Launcher ของเกม'
        Say "  shortcut จะเช็ก/ซ่อมคำแปลก่อน แล้วเปิดเกมผ่าน $how ให้เอง"
        Say "  (ถ้าเปิดจาก $how ตรง ๆ ก็เล่นได้ แต่ม็อดจะไม่ได้เช็กอัปเดตรอบนั้น)"
        Say '  หลังเกมอัปเดต ให้เปิดผ่านไอคอนนี้ ม็อดจะให้เกมอัปเดตภาษาก่อน แล้วกลับมาเองรอบถัดไป'
    } catch {
        Say "สร้าง shortcut ไม่สำเร็จ: $($_.Exception.Message)" 'Yellow'
        Say "  เปิดเกมด้วย $(Join-Path $ModHome 'play.bat') แทนได้"
    }
}

function Main-Install {
    Say '=== ม็อดแปลไทย Where Winds Meet: ติดตั้ง ===' 'Cyan'
    if (Test-GameRunning) { Say 'เกมเปิดอยู่: ปิดเกมก่อน แล้วรัน install.bat ใหม่' 'Red'; $script:ExitCode = 1; return }
    $src = $PSScriptRoot
    $kitRaw = Read-KV (Join-Path $src 'data\manifest.txt')
    if (-not $kitRaw['mod_version']) { Say 'ไม่พบโฟลเดอร์ data: แตกไฟล์ zip ทั้งหมดก่อน แล้วรันจากโฟลเดอร์ที่แตกออกมา' 'Red'; $script:ExitCode = 1; return }
    $games = @(Select-Games)
    if (-not $games.Count) { Say 'ยกเลิก: ไม่ได้ระบุโฟลเดอร์เกม' 'Red'; $script:ExitCode = 1; return }

    $script:Installed = @()
    $tmp = Join-Path $env:TEMP ('wwmthai_' + [guid]::NewGuid().ToString('N'))
    try {
        foreach ($game in $games) {
            if ($games.Count -gt 1) { Say ''; Say "----- $game -----" 'Cyan' }
            try { Install-One $game $src $kitRaw $tmp }
            catch { Say "เกิดข้อผิดพลาด: $($_.Exception.Message)" 'Red'; Log ($_ | Out-String); $script:ExitCode = 1 }
        }
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not $script:Installed.Count) { return }

    # คัดลอกสคริปต์ไปเก็บไว้ที่ %LOCALAPPDATA%\WWM-Thai (ลบโฟลเดอร์ที่แตก zip ทิ้งได้หลังติดตั้ง)
    $same = (Resolve-Path -LiteralPath $src).Path.TrimEnd('\') -eq (Resolve-Path -LiteralPath $ModHome).Path.TrimEnd('\')
    if (-not $same) {
        foreach ($n in 'wwm-thai.ps1', 'play.bat', 'uninstall.bat', 'README.txt') {
            $p = Join-Path $src $n
            if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination $ModHome -Force }
        }
    }
    Get-ChildItem -LiteralPath $ModHome -Recurse -File | Unblock-File
    $steam = $false
    foreach ($game in $script:Installed) {
        if ((Get-Platform $game) -eq 'steam') { $steam = $true } else { Show-PlayShortcut $game }
    }
    if ($steam) { Show-LaunchOption }
}

# ติดตั้งลงเกมเดียว (สำเร็จ = เพิ่มเข้า $script:Installed)
function Install-One([string]$game, [string]$src, [hashtable]$kitRaw, [string]$tmp) {
    $platform = Get-Platform $game
    Set-Game $game
    $kitMan = Get-ModMan $kitRaw
    Say "พบเกมที่: $game  ($platform)"
    Say "ม็อดเวอร์ชัน: $($kitMan['mod_version'])  (สร้างสำหรับเกมเวอร์ชัน $($kitMan['game_build']))"
    Write-Diagnostics $game $kitMan

    $oldMan = Get-ModMan (Read-KV (Join-Path $DataDir 'manifest.txt'))
    $orig = Get-GameOrig $game $oldMan
    $kitOk = Test-Compatible $orig $kitMan
    $oldOk = [bool]$oldMan['mod_version'] -and (Test-Compatible $orig $oldMan)

    # เลือกชุดข้อมูลที่ใหม่สุดที่เข้ากับเกม: release บน GitHub > ที่ติดตั้งไว้แล้ว > ใน zip
    # (รัน install.bat ทับของเดิมได้เสมอ = อัปเดตด้วยมือได้ และไม่ถอยเวอร์ชันลง)
    $best = $null; $bestVer = [version]'0.0'; $checked = ''
    if ($kitOk) { $best = Join-Path $src 'data'; $bestVer = [version]$kitMan['mod_version'] }
    if ($oldOk -and [version]$oldMan['mod_version'] -gt $bestVer) { $best = $DataDir; $bestVer = [version]$oldMan['mod_version'] }
    if ($Repo) {
        Say 'เช็กเวอร์ชันล่าสุดบน GitHub...' 'Cyan'
        try {
            $u = Find-Update $orig $bestVer
            if ($u) {
                $best = Get-Update $u $tmp; $bestVer = $u.Version
                Say "พบม็อดเวอร์ชันใหม่กว่า: $bestVer (ใช้ตัวนี้แทนของใน zip)" 'Green'
            } else { if ($best) { Say "ไม่มีเวอร์ชันใหม่กว่า $bestVer" }; Log 'install: no newer release' }
            $checked = (Get-Date).ToString('s')
        } catch {
            Say "เช็กอัปเดตไม่สำเร็จ (ใช้ของใน zip แทน): $($_.Exception.Message)" 'Yellow'
            Log ($_ | Out-String)
        }
    }
    if (-not $best) {
        Say 'ตรวจเวอร์ชันเกม...  ไม่ตรงกับม็อดชุดนี้ (เกมอาจอัปเดตแล้ว)' 'Red'
        Say 'และยังไม่พบม็อดเวอร์ชันที่ตรงกับเกมบน GitHub: ไม่ได้แก้ไขไฟล์ใด ๆ รอม็อดเวอร์ชันใหม่ก่อน' 'Red'
        $script:ExitCode = 1; return
    }
    Say "ตรวจเวอร์ชันเกม...  ตรงกับม็อด $bestVer" 'Green'

    New-Item -ItemType Directory -Force -Path $script:ProfileDir | Out-Null
    if ($best -eq $DataDir) {
        Install-Data $game $oldMan $DataDir   # ของที่ติดตั้งไว้ใหม่สุดอยู่แล้ว: แค่ซ่อมให้ครบ
        $man = $oldMan
    } else {
        $man = Use-Kit $game $oldMan $best
    }
    $st = Read-KV $StateFile; $st['game_path'] = $game
    if ($checked) { $st['last_check'] = $checked }
    if ($script:SA) { $st['sa_patch_ver'] = Get-PatchVer $game }
    Write-KV $StateFile $st
    Say "สำรองไฟล์ต้นฉบับไว้ที่: $BackupDir"
    Say "ติดตั้งสำเร็จ! (ม็อด $($man['mod_version'])) เข้าเกมแล้วตั้งภาษาเป็น ไทย" 'Green'
    $script:Installed += $game
}

function Main-Play {
    # มี -GameExe = ถูกเรียกจาก Steam Launch Options (play.bat เปิดเกมเองหลังจากนี้)
    # ไม่มี = เปิดจาก shortcut: เช็ก/ซ่อมแล้วสคริปต์นี้เปิดเกมให้ (Steam / launcher ของเกม)
    $launch = -not $GameExe
    if ($launch) {
        $game = if ($Game) { Resolve-GameDir $Game } else { $null }   # shortcut ระบุเกมไว้
        if (-not $game) { $game = Find-PlayGame }
        if (-not $game) { Say 'หาโฟลเดอร์เกมไม่เจอ: รัน install.bat ก่อน' 'Red'; $script:ExitCode = 1; return }
        Set-Game $game
        try { Update-Mod $game } catch { Say "เกิดข้อผิดพลาด: $($_.Exception.Message)" 'Red'; Log ($_ | Out-String) }
        Start-Game $game
        return
    }
    $game = Resolve-GameDir $GameExe
    if (-not $game) { Say "ไม่พบไฟล์ภาษาของเกมจาก '$GameExe': ข้ามม็อด" 'Yellow'; return }
    Set-Game $game
    Update-Mod $game
}

# บันทึกข้อมูลสำหรับแก้ปัญหาลง log.txt (แพลตฟอร์ม, ที่อยู่ไฟล์, เวอร์ชันเกม, SHA256 เทียบกับ manifest)
function Write-Diagnostics([string]$game, [hashtable]$man) {
    try {
        $bv = Join-Path $game 'Engine\Binaries\Win64r\Built.version'
        $ver = if (Test-Path -LiteralPath $bv) { (Get-Content -LiteralPath $bv -Raw).Trim() } else { '?' }
        Log "diag: profile=$script:ProfileDir"
        Log "diag: platform=$(Get-Platform $game) variant=$($man['_variant']) game=$game locale=$(Get-LocaleDir $game) built=$ver patch=$(Get-PatchVer $game) mod=$($man['mod_version']) mod_built=$($man['game_build'])"
        foreach ($f in $Files) {
            $h = Hash (GameFile $game $f)
            $what = if (-not $h) { 'MISSING' } elseif ($h -eq $man["orig_$f"]) { 'orig (ok)' } elseif ($h -eq $man["mod_$f"]) { 'mod' } else { 'OTHER' }
            Log "diag: $f sha256=$h -> $what"
        }
        $l = Get-Launcher $game
        if ($l) { Log "diag: launcher=$l" }
    } catch { Log "diag failed: $($_.Exception.Message)" }
}

function Update-Mod([string]$game) {
    $st = Read-KV $StateFile; $st['game_path'] = $game
    $man = Get-ModMan (Read-KV (Join-Path $DataDir 'manifest.txt'))
    if ($man['mod_version']) { Write-Diagnostics $game $man }
    if (-not $man['mod_version']) { Say 'ยังไม่ได้ติดตั้งม็อด (รัน install.bat ก่อน): เปิดเกมตามปกติ' 'Yellow'; return }
    if ($script:SA) {
        # เกมอัปเดตตั้งแต่รอบก่อน: ไฟล์ read-only ของม็อดทำให้ patcher อัปเดตไฟล์ภาษาไม่ได้
        # -> คืนต้นฉบับ (ปลด read-only) ให้ patcher เขียนไฟล์ใหม่ รอบหน้าค่อยติดตั้งม็อดใหม่
        $pv = Get-PatchVer $game
        $prev = $st['sa_patch_ver']
        $st['sa_patch_ver'] = $pv
        if ($prev -and $pv -and $pv -ne $prev -and (Get-Status $game $man) -eq 'mod') {
            Log "patch version changed: $prev -> $pv"
            if (Restore-Original $game $man) {
                Say 'เกมเพิ่งอัปเดต: คืนไฟล์ภาษาต้นฉบับให้เกมอัปเดตไฟล์ภาษาก่อน' 'Yellow'
                Say '  รอบนี้จะเป็นภาษาไทยเดิมของเกม เปิดผ่าน shortcut ครั้งหน้า ม็อดจะกลับมาเอง' 'Yellow'
            }
            Write-KV $StateFile $st
            return
        }
    }
    $orig = Get-GameOrig $game $man
    $compatible = Test-Compatible $orig $man

    if ($Repo) {   # เช็กทุกครั้งที่กด Play (ปกติ 1 request; ไม่มีเน็ตก็แค่ข้ามไป)
        $tmp = Join-Path $env:TEMP ('wwmthai_' + [guid]::NewGuid().ToString('N'))
        try {
            $min = if ($compatible -and $man['mod_version']) { [version]$man['mod_version'] } else { [version]'0.0' }
            $u = Find-Update $orig $min
            if ($u) {
                New-Item -ItemType Directory -Path $tmp | Out-Null
                $man = Use-Kit $game $man (Get-Update $u $tmp)
                Say "อัปเดตม็อดเป็นเวอร์ชัน $($man['mod_version']) แล้ว" 'Green'
            } else { Log 'no newer release' }
            $st['last_check'] = (Get-Date).ToString('s')
        } catch {
            Say "เช็กอัปเดตไม่สำเร็จ (จะลองใหม่ครั้งหน้า): $($_.Exception.Message)" 'Yellow'
        } finally {
            Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    Write-KV $StateFile $st

    switch (Get-Status $game $man) {
        'mod'   { Say "ภาษาไทย (ม็อด $($man['mod_version'])) พร้อมแล้ว" 'Green' }
        'orig'  { Install-Data $game $man $DataDir; Say "ติดตั้งคำแปลไทย (ม็อด $($man['mod_version'])) ใหม่แล้ว" 'Green' }
        default { Say 'เกมอัปเดตแล้ว แต่ม็อดเวอร์ชันที่ตรงกับเกมยังไม่ออก: รอบนี้เกมจะใช้ภาษาไทยเดิมไปก่อน' 'Yellow' }
    }
}

function Main-Uninstall {
    Say '=== ม็อดแปลไทย Where Winds Meet: ถอนการติดตั้ง ===' 'Cyan'
    if (Test-GameRunning) { Say 'เกมเปิดอยู่: ปิดเกมก่อน แล้วรัน uninstall.bat ใหม่' 'Red'; $script:ExitCode = 1; return }
    $games = @(Select-Games -Installed)
    if (-not $games.Count) {
        if (@(Get-ModGames).Count) { Say 'ยกเลิก' 'Red'; $script:ExitCode = 1; return }
        Say 'ไม่พบเกมที่ลงม็อดไว้' 'Yellow'
    }
    foreach ($game in $games) { Uninstall-One $game }
    if (-not @(Get-ModGames).Count) {
        foreach ($s in @(Get-PlayShortcuts)) { Remove-Item -LiteralPath $s.Path -Force; Say 'ลบ shortcut บน Desktop แล้ว' }
    }
    Say ''
    Say "ไฟล์ม็อดอยู่ที่ $ModHome (ถ้าไม่ได้ลงม็อดไว้ที่เกมไหนแล้ว ลบทิ้งได้)"
}
function Uninstall-One([string]$game) {
    Say ''
    Say "เกมที่: $game"
    Set-Game $game
    $man = Get-ModMan (Read-KV (Join-Path $DataDir 'manifest.txt'))
    $platform = Get-Platform $game
    if (-not (Restore-Original $game $man)) {
        $verify = switch ($platform) {
            'steam' { 'Steam > คลิกขวาที่เกม > Properties > Installed Files > Verify integrity of game files' }
            default { 'ปุ่มตรวจสอบ/ซ่อมไฟล์ (Verify / Repair) ใน Launcher ของเกม' }
        }
        Say "คืนไฟล์บางไฟล์ไม่ได้: ใช้ $verify" 'Yellow'
        $script:ExitCode = 1
        return
    }
    Say 'คืนไฟล์ภาษาไทยต้นฉบับของเกมแล้ว' 'Green'
    Remove-Item -LiteralPath $script:ProfileDir -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($s in @(Get-PlayShortcuts | Where-Object { $_.Game -eq $game })) {
        Remove-Item -LiteralPath $s.Path -Force; Say 'ลบ shortcut บน Desktop แล้ว'
    }
    if ($platform -eq 'steam') { Say 'อย่าลืม: ลบบรรทัด play.bat ออกจาก Steam > Properties > Launch Options' 'Cyan' }
}

try {
    Move-Legacy
    switch ($Mode) {
        'install'   { Main-Install }
        'play'      { Main-Play }
        'uninstall' { Main-Uninstall }
    }
} catch {
    Say "เกิดข้อผิดพลาด: $($_.Exception.Message)" 'Red'
    Log ($_ | Out-String)
    $script:ExitCode = 1
}
exit $script:ExitCode
