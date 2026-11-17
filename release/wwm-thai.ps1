# =====================================================================
#  ม็อดแปลไทย Where Winds Meet — ตัวติดตั้ง / อัปเดต / ถอนการติดตั้ง
#
#  ทำงานด้วย Windows PowerShell ที่มากับ Windows (ไม่ต้องลงโปรแกรมเพิ่ม)
#  ถูกเรียกจาก install.bat / play.bat / uninstall.bat
#
#  ไฟล์ในเกมที่สคริปต์นี้แก้ไข มีแค่ 2 ไฟล์:
#    <โฟลเดอร์เกม>\Package\HD\oversea\locale\translate_words_map_th          (Steam / Epic)
#    <โฟลเดอร์เกม>\Package\HD\oversea\locale\translate_words_map_th_diff
#  ตัวติดตั้งของเกมเอง (standalone, beta) ใช้ LocalData\Patch\HD\oversea\locale แทน
#  และตั้งไฟล์ม็อดเป็น read-only เพราะ launcher คอยเขียนไฟล์ในโฟลเดอร์นั้นคืน
#
#  กติกาความปลอดภัย:
#   - ก่อนแก้ไฟล์ จะสำรองต้นฉบับไว้ที่ %LOCALAPPDATA%\WWM-Thai\backup เสมอ
#   - จะวางไฟล์ม็อดก็ต่อเมื่อไฟล์ในเกมตรงกับเวอร์ชันที่ม็อดสร้างมา (เช็ก SHA256)
#     ถ้าเกมอัปเดตแล้วไม่ตรง จะไม่แตะอะไรเลย (กันข้อความในเกมเพี้ยน)
#   - อัปเดตอัตโนมัติจะโหลดจาก GitHub Releases ของ $Repo เท่านั้น
#     ตรวจ SHA256 ก่อนใช้ และแทนที่เฉพาะ "ไฟล์ข้อมูลภาษา" — ไม่เคยแทนที่สคริปต์
# =====================================================================
param(
    [Parameter(Mandatory = $true)][ValidateSet('install', 'play', 'uninstall')][string]$Mode,
    [string]$GameExe = ''
)
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

# ---------------- ตั้งค่า ----------------
$Repo            = ''   # GitHub "owner/repo" สำหรับอัปเดตอัตโนมัติ (ว่าง = ไม่เช็กออนไลน์) — make_release ใส่ให้
$Files           = @('translate_words_map_th', 'translate_words_map_th_diff')
# ที่เก็บไฟล์ภาษา: Steam / Epic ใช้ Package\HD, ตัวติดตั้งของเกมเอง (standalone) ใช้ LocalData\Patch\HD
$LocaleRels      = @('Package\HD\oversea\locale', 'LocalData\Patch\HD\oversea\locale')
$SteamAppId      = '3564740'
# Epic: ใช้ค่าจาก manifest ของ Epic ก่อน ค่านี้เป็นค่าสำรอง (ค่าเดียวกับที่ม็อด wwm_brasileiro ใช้)
$EpicUriDefault  = 'com.epicgames.launcher://apps/4806012311744989a5f96d97a42f7829%3Ad53f8dc5825748849ca0890279c3dad7%3Aa7d28f0e0935490b9d6f92dda1a7a75b?action=launch&silent=true'
$ShortcutName    = 'Where Winds Meet (Thai).lnk'   # WScript.Shell บันทึกชื่อไฟล์ภาษาไทยไม่ได้

$ModHome   = if ($env:WWMTHAI_HOME) { $env:WWMTHAI_HOME } else { Join-Path $env:LOCALAPPDATA 'WWM-Thai' }
$DataDir   = Join-Path $ModHome 'data'
$BackupDir = Join-Path $ModHome 'backup'
$StateFile = Join-Path $ModHome 'state.txt'
$LogFile   = Join-Path $ModHome 'log.txt'
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

# ---------------- หาโฟลเดอร์เกม (Steam / Epic / ตัวติดตั้งของเกม) ----------------
# แปลงสิ่งที่ผู้ใช้ให้มา (โฟลเดอร์เกม, wwm.exe, launcher.exe หรือโฟลเดอร์ wwm ที่มี wwm_standard) เป็นโฟลเดอร์เกม
function Resolve-GameDir([string]$p) {
    if (-not $p) { return $null }
    $p = $p.Trim().Trim('"')
    if (Test-Path -LiteralPath $p -PathType Leaf) {
        if ((Split-Path $p -Leaf) -ieq 'wwm.exe') { for ($i = 0; $i -lt 4; $i++) { $p = Split-Path $p } }
        else { $p = Split-Path $p }   # เช่น launcher.exe ของตัวติดตั้งเกม
    }
    foreach ($c in @($p, (Join-Path $p 'wwm_standard'), (Join-Path $p 'wwm_lite'))) {
        if (Test-Game $c) { return $c }
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
# Epic เก็บข้อมูลเกมที่ติดตั้งไว้เป็นไฟล์ JSON (*.item)
function Get-EpicItems {
    $dir = Join-Path $env:ProgramData 'Epic\EpicGamesLauncher\Data\Manifests'
    if (-not (Test-Path -LiteralPath $dir)) { return }
    foreach ($f in Get-ChildItem -LiteralPath $dir -Filter '*.item' -ErrorAction SilentlyContinue) {
        try {
            $j = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($j.DisplayName -match 'Where Winds Meet' -and $j.InstallLocation) { $j }
        } catch {}
    }
}
function Get-EpicGames { foreach ($j in Get-EpicItems) { Resolve-GameDir $j.InstallLocation } }
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
    foreach ($g in @(Get-SteamGames) + @(Get-EpicGames) + @(Get-StandaloneGames)) {
        if ($g -and -not $seen.ContainsKey($g.ToLower())) { $seen[$g.ToLower()] = $true; $g }
    }
}
function Get-Platform([string]$game) {
    if ($game -match '\\steamapps\\common\\') { return 'steam' }
    foreach ($j in Get-EpicItems) { if ((Resolve-GameDir $j.InstallLocation) -eq $game) { return 'epic' } }
    if ((Split-Path $game -Leaf) -match '^wwm_(standard|lite)$' -or (Get-LocaleDir $game) -like '*\LocalData\*') { return 'standalone' }
    return 'other'
}
function Find-Game([switch]$Ask) {
    if ($env:WWMTHAI_GAME) { return (Resolve-GameDir $env:WWMTHAI_GAME) }   # สำหรับทดสอบ
    $st = Read-KV $StateFile
    if (Test-Game $st['game_path']) { return $st['game_path'] }
    $all = @(Find-AllGames)
    if ($all.Count -eq 1) { return $all[0] }
    if (-not $Ask) { if ($all.Count) { return $all[0] } else { return $null } }
    if ($all.Count -gt 1) {
        Say 'พบเกมมากกว่าหนึ่งที่:' 'Yellow'
        for ($i = 0; $i -lt $all.Count; $i++) { Say ("  [{0}] {1}  ({2})" -f ($i + 1), $all[$i], (Get-Platform $all[$i])) }
        $n = Read-Host 'เลือกหมายเลข'
        if ($n -match '^\d+$' -and [int]$n -ge 1 -and [int]$n -le $all.Count) { return $all[[int]$n - 1] }
    }
    while ($true) {
        Say 'หาโฟลเดอร์เกมไม่เจอ: ลากโฟลเดอร์เกม (หรือไฟล์ wwm.exe / launcher.exe) มาวางในหน้าต่างนี้ แล้วกด Enter (กด Enter เปล่า ๆ = ยกเลิก)' 'Yellow'
        $p = Read-Host 'โฟลเดอร์เกม'
        if (-not $p.Trim()) { return $null }
        $g = Resolve-GameDir $p
        if ($g) { return $g }
        Say "ไม่พบไฟล์ภาษาของเกมใน: $p" 'Red'
    }
}

# ---------------- เปิดเกม (สำหรับ shortcut / Epic / ตัวติดตั้งของเกม) ----------------
function Get-EpicUri([string]$game) {
    foreach ($j in Get-EpicItems) {
        if ((Resolve-GameDir $j.InstallLocation) -eq $game -and $j.CatalogNamespace -and $j.CatalogItemId -and $j.AppName) {
            return "com.epicgames.launcher://apps/$($j.CatalogNamespace)%3A$($j.CatalogItemId)%3A$($j.AppName)?action=launch&silent=true"
        }
    }
    return $EpicUriDefault
}
function Start-Game([string]$game) {
    $platform = Get-Platform $game
    $target = switch ($platform) {
        'steam' { "steam://rungameid/$SteamAppId" }
        'epic'  { Get-EpicUri $game }
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
function Get-ShortcutPath {
    $desk = if ($env:WWMTHAI_DESKTOP) { $env:WWMTHAI_DESKTOP } else { [Environment]::GetFolderPath('Desktop') }   # override สำหรับทดสอบ
    return Join-Path $desk $ShortcutName
}
function New-PlayShortcut {
    $lnk = Get-ShortcutPath
    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($lnk)
    $s.TargetPath = Join-Path $ModHome 'play.bat'
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
function Get-Update($u, [string]$tmp) {
    $zip = Join-Path $tmp 'mod.zip'
    Say "กำลังดาวน์โหลดม็อดเวอร์ชัน $($u.Version) ..." 'Cyan'
    Get-Web $u.Url $zip | Out-Null
    if ((Hash $zip) -ne $u.Man['zip_sha256']) { throw 'ไฟล์ที่ดาวน์โหลดไม่ตรงกับ SHA256 ที่ประกาศไว้' }
    Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $tmp 'x')
    $inner = Get-ChildItem -LiteralPath (Join-Path $tmp 'x') -Recurse -Filter 'manifest.txt' |
        Where-Object { $_.Directory.Name -eq 'data' } | Select-Object -First 1
    if (-not $inner) { throw 'ไม่พบข้อมูลภาษาในไฟล์ที่ดาวน์โหลด' }
    $m = Get-ModMan (Read-KV $inner.FullName)
    foreach ($f in $Files) {
        if ($m["mod_$f"] -ne $u.Man["mod_$f"] -or (Hash (Join-Path $inner.DirectoryName (Src $m $f))) -ne $m["mod_$f"]) {
            throw "ไฟล์ $f ในชุดอัปเดตไม่ถูกต้อง"
        }
    }
    return $inner.DirectoryName
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
# Epic / ตัวติดตั้งของเกม ใส่คำสั่งก่อนเปิดเกมไม่ได้ จึงให้เปิดเกมผ่าน shortcut บน Desktop แทน
function Show-PlayShortcut([string]$platform) {
    Say ''
    try {
        $lnk = New-PlayShortcut
        Say 'อยากให้ม็อดอัปเดตเองทุกครั้งที่เล่น (แนะนำ):' 'Cyan'
        Say "  เปิดเกมจาก shortcut บน Desktop: $([IO.Path]::GetFileNameWithoutExtension($lnk))" 'White'
        $how = if ($platform -eq 'epic') { 'Epic Games Launcher' } else { 'launcher ของเกม' }
        Say "  shortcut จะเช็ก/ซ่อมคำแปลก่อน แล้วเปิดเกมผ่าน $how ให้เอง"
        Say "  (ถ้าเปิดจาก $how ตรง ๆ ก็เล่นได้ แต่ม็อดจะไม่ได้เช็กอัปเดตรอบนั้น)"
        if ($platform -ne 'epic') {
            Say 'ตัวติดตั้งของเกม (standalone) รองรับแบบทดลอง (beta):' 'Yellow'
            Say '  ไฟล์ภาษาของม็อดถูกตั้งเป็น read-only เพื่อไม่ให้ launcher เขียนทับ'
            Say '  หลังเกมอัปเดต ให้เปิดผ่าน shortcut นี้ ม็อดจะคืนไฟล์ให้เกมอัปเดตภาษาก่อน แล้วกลับมาเองรอบถัดไป'
        }
    } catch {
        Say "สร้าง shortcut ไม่สำเร็จ: $($_.Exception.Message)" 'Yellow'
        Say "  เปิดเกมด้วย $(Join-Path $ModHome 'play.bat') แทนได้"
    }
}

function Main-Install {
    Say '=== ม็อดแปลไทย Where Winds Meet: ติดตั้ง ===' 'Cyan'
    if (Test-GameRunning) { Say 'เกมเปิดอยู่: ปิดเกมก่อน แล้วรัน install.bat ใหม่' 'Red'; $script:ExitCode = 1; return }
    $src = $PSScriptRoot
    $kitMan = Read-KV (Join-Path $src 'data\manifest.txt')
    if (-not $kitMan['mod_version']) { Say 'ไม่พบโฟลเดอร์ data: แตกไฟล์ zip ทั้งหมดก่อน แล้วรันจากโฟลเดอร์ที่แตกออกมา' 'Red'; $script:ExitCode = 1; return }
    $game = Find-Game -Ask
    if (-not $game) { Say 'ยกเลิก: ไม่ได้ระบุโฟลเดอร์เกม' 'Red'; $script:ExitCode = 1; return }
    $platform = Get-Platform $game
    Set-Variant $game
    $kitMan = Get-ModMan $kitMan
    Say "พบเกมที่: $game  ($platform)"
    Say "ม็อดเวอร์ชัน: $($kitMan['mod_version'])  (สร้างสำหรับเกมเวอร์ชัน $($kitMan['game_build']))"
    Write-Diagnostics $game $kitMan

    $oldMan = Get-ModMan (Read-KV (Join-Path $DataDir 'manifest.txt'))
    $orig = Get-GameOrig $game $oldMan
    $kitOk = Test-Compatible $orig $kitMan
    $oldOk = [bool]$oldMan['mod_version'] -and (Test-Compatible $orig $oldMan)

    # เลือกชุดข้อมูลที่ใหม่สุดที่เข้ากับเกม: release บน GitHub > ที่ติดตั้งไว้แล้ว > ใน zip
    # (รัน install.bat ทับของเดิมได้เสมอ = อัปเดตด้วยมือได้ และไม่ถอยเวอร์ชันลง)
    $best = $null; $bestVer = [version]'0.0'
    if ($kitOk) { $best = Join-Path $src 'data'; $bestVer = [version]$kitMan['mod_version'] }
    if ($oldOk -and [version]$oldMan['mod_version'] -gt $bestVer) { $best = $DataDir; $bestVer = [version]$oldMan['mod_version'] }
    $tmp = Join-Path $env:TEMP ('wwmthai_' + [guid]::NewGuid().ToString('N'))
    try {
        if ($Repo) {
            Say 'เช็กเวอร์ชันล่าสุดบน GitHub...' 'Cyan'
            try {
                $u = Find-Update $orig $bestVer
                if ($u) {
                    New-Item -ItemType Directory -Path $tmp | Out-Null
                    $best = Get-Update $u $tmp; $bestVer = $u.Version
                    Say "พบม็อดเวอร์ชันใหม่กว่า: $bestVer (ใช้ตัวนี้แทนของใน zip)" 'Green'
                } else { if ($best) { Say "ไม่มีเวอร์ชันใหม่กว่า $bestVer" }; Log 'install: no newer release' }
                $st = Read-KV $StateFile; $st['last_check'] = (Get-Date).ToString('s'); Write-KV $StateFile $st
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

        # คัดลอกสคริปต์ไปเก็บไว้ที่ %LOCALAPPDATA%\WWM-Thai (ลบโฟลเดอร์ที่แตก zip ทิ้งได้หลังติดตั้ง)
        $same = (Resolve-Path -LiteralPath $src).Path.TrimEnd('\') -eq (Resolve-Path -LiteralPath $ModHome).Path.TrimEnd('\')
        if (-not $same) {
            foreach ($n in 'wwm-thai.ps1', 'play.bat', 'uninstall.bat', 'README.txt') {
                $p = Join-Path $src $n
                if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination $ModHome -Force }
            }
        }
        if ($best -eq $DataDir) {
            Install-Data $game $oldMan $DataDir   # ของที่ติดตั้งไว้ใหม่สุดอยู่แล้ว: แค่ซ่อมให้ครบ
            $man = $oldMan
        } else {
            $man = Use-Kit $game $oldMan $best
        }
        Get-ChildItem -LiteralPath $ModHome -Recurse -File | Unblock-File
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    $st = Read-KV $StateFile; $st['game_path'] = $game
    if ($script:SA) { $st['sa_patch_ver'] = Get-PatchVer $game }
    Write-KV $StateFile $st
    Say "สำรองไฟล์ต้นฉบับไว้ที่: $BackupDir"
    Say "ติดตั้งสำเร็จ! (ม็อด $($man['mod_version'])) เข้าเกมแล้วตั้งภาษาเป็น ไทย" 'Green'
    if ($platform -eq 'steam') { Show-LaunchOption } else { Show-PlayShortcut $platform }
}

function Main-Play {
    # มี -GameExe = ถูกเรียกจาก Steam Launch Options (play.bat เปิดเกมเองหลังจากนี้)
    # ไม่มี = เปิดจาก shortcut: เช็ก/ซ่อมแล้วสคริปต์นี้เปิดเกมให้ (Steam / Epic / launcher ของเกม)
    $launch = -not $GameExe
    if ($launch) {
        $game = Find-Game
        if (-not $game) { Say 'หาโฟลเดอร์เกมไม่เจอ: รัน install.bat ก่อน' 'Red'; $script:ExitCode = 1; return }
        Set-Variant $game
        try { Update-Mod $game } catch { Say "เกิดข้อผิดพลาด: $($_.Exception.Message)" 'Red'; Log ($_ | Out-String) }
        Start-Game $game
        return
    }
    $game = Resolve-GameDir $GameExe
    if (-not $game) { Say "ไม่พบไฟล์ภาษาของเกมจาก '$GameExe': ข้ามม็อด" 'Yellow'; return }
    Set-Variant $game
    Update-Mod $game
}

# บันทึกข้อมูลสำหรับแก้ปัญหาลง log.txt (แพลตฟอร์ม, ที่อยู่ไฟล์, เวอร์ชันเกม, SHA256 เทียบกับ manifest)
function Write-Diagnostics([string]$game, [hashtable]$man) {
    try {
        $bv = Join-Path $game 'Engine\Binaries\Win64r\Built.version'
        $ver = if (Test-Path -LiteralPath $bv) { (Get-Content -LiteralPath $bv -Raw).Trim() } else { '?' }
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
    $game = Find-Game -Ask
    if (-not $game) { Say 'ยกเลิก: ไม่ได้ระบุโฟลเดอร์เกม' 'Red'; $script:ExitCode = 1; return }
    Say "เกมที่: $game"
    Set-Variant $game
    $man = Get-ModMan (Read-KV (Join-Path $DataDir 'manifest.txt'))
    $platform = Get-Platform $game
    if (-not (Restore-Original $game $man)) {
        $verify = switch ($platform) {
            'steam' { 'Steam > คลิกขวาที่เกม > Properties > Installed Files > Verify integrity of game files' }
            'epic'  { 'Epic Games Launcher > Library > ... ที่เกม > Manage > Verify' }
            default { 'ปุ่มตรวจสอบ/ซ่อมไฟล์ (Verify / Repair) ใน launcher ของเกม' }
        }
        Say "คืนไฟล์บางไฟล์ไม่ได้: ใช้ $verify" 'Yellow'
        $script:ExitCode = 1
    } else {
        Say 'คืนไฟล์ภาษาไทยต้นฉบับของเกมแล้ว' 'Green'
    }
    $lnk = Get-ShortcutPath
    if (Test-Path -LiteralPath $lnk) { Remove-Item -LiteralPath $lnk -Force; Say 'ลบ shortcut บน Desktop แล้ว' }
    Say ''
    if ($platform -eq 'steam') { Say 'อย่าลืม: ลบบรรทัด play.bat ออกจาก Steam > Properties > Launch Options' 'Cyan' }
    Say "ไฟล์ม็อดและไฟล์สำรองอยู่ที่ $ModHome (ลบทิ้งได้)"
}

try {
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
