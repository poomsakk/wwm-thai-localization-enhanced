# =====================================================================
#  ม็อดแปลไทย Where Winds Meet — ตัวติดตั้ง / อัปเดต / ถอนการติดตั้ง
#
#  ทำงานด้วย Windows PowerShell ที่มากับ Windows (ไม่ต้องลงโปรแกรมเพิ่ม)
#  ถูกเรียกจาก install.bat / play.bat / uninstall.bat
#
#  ไฟล์ในเกมที่สคริปต์นี้แก้ไข มีแค่ 2 ไฟล์:
#    <โฟลเดอร์เกม>\Package\HD\oversea\locale\translate_words_map_th
#    <โฟลเดอร์เกม>\Package\HD\oversea\locale\translate_words_map_th_diff
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
$LocaleRel       = 'Package\HD\oversea\locale'

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
function GameFile([string]$game, [string]$f) { return Join-Path $game "$LocaleRel\$f" }
function Test-Game([string]$dir) { return [bool]($dir -and (Test-Path -LiteralPath (GameFile $dir $Files[0]))) }
function Test-GameRunning { return [bool](Get-Process -Name 'wwm' -ErrorAction SilentlyContinue) }

# ---------------- หาโฟลเดอร์เกม ----------------
function Find-Game([switch]$Ask) {
    if ($env:WWMTHAI_GAME) { return $env:WWMTHAI_GAME }
    $st = Read-KV $StateFile
    if (Test-Game $st['game_path']) { return $st['game_path'] }
    # ค้นจากคลังเกมของ Steam (registry + libraryfolders.vdf)
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
    foreach ($lib in $libs) {
        $d = Join-Path $lib 'steamapps\common\Where Winds Meet'
        if (Test-Game $d) { return $d }
    }
    if (-not $Ask) { return $null }
    while ($true) {
        Say 'หาโฟลเดอร์เกมไม่เจอ: ลากโฟลเดอร์ "Where Winds Meet" มาวางในหน้าต่างนี้ แล้วกด Enter (กด Enter เปล่า ๆ = ยกเลิก)' 'Yellow'
        $p = (Read-Host 'โฟลเดอร์เกม').Trim().Trim('"')
        if (-not $p) { return $null }
        if (Test-Path -LiteralPath $p -PathType Leaf) { for ($i = 0; $i -lt 4; $i++) { $p = Split-Path $p } }  # ลาก wwm.exe มาก็ได้
        if (Test-Game $p) { return $p }
        Say "ไม่พบไฟล์ภาษาของเกมใน: $p" 'Red'
    }
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
        if ($h -eq $man["mod_$f"]) { continue }
        if ($h -ne $man["orig_$f"]) { throw "ไฟล์ $f ในเกมไม่ตรงกับเวอร์ชันที่ม็อดรองรับ" }
        $bak = Join-Path $BackupDir $f
        if ((Hash $bak) -ne $h) {
            Copy-Item -LiteralPath $dst -Destination $bak -Force
            if ((Hash $bak) -ne $h) { throw "สำรองไฟล์ $f ไม่สำเร็จ" }
        }
        Copy-Item -LiteralPath (Join-Path $dataDir $f) -Destination $dst -Force
        if ((Hash $dst) -ne $man["mod_$f"]) {
            Copy-Item -LiteralPath $bak -Destination $dst -Force
            throw "คัดลอกไฟล์ $f ไม่สำเร็จ (คืนไฟล์เดิมให้แล้ว)"
        }
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
    $newMan = Read-KV (Join-Path $newDataDir 'manifest.txt')
    if (-not (Restore-Original $game $oldMan)) { throw 'คืนไฟล์ต้นฉบับก่อนเปลี่ยนเวอร์ชันไม่สำเร็จ' }
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
    foreach ($f in @($Files) + 'manifest.txt') {
        Copy-Item -LiteralPath (Join-Path $newDataDir $f) -Destination (Join-Path $DataDir $f) -Force
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
        try { Get-Web $ma.browser_download_url $tmp | Out-Null; $m = Read-KV $tmp } finally { Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue }
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
    $m = Read-KV $inner.FullName
    foreach ($f in $Files) {
        if ($m["mod_$f"] -ne $u.Man["mod_$f"] -or (Hash (Join-Path $inner.DirectoryName $f)) -ne $m["mod_$f"]) {
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

function Main-Install {
    Say '=== ม็อดแปลไทย Where Winds Meet: ติดตั้ง ===' 'Cyan'
    if (Test-GameRunning) { Say 'เกมเปิดอยู่: ปิดเกมก่อน แล้วรัน install.bat ใหม่' 'Red'; $script:ExitCode = 1; return }
    $src = $PSScriptRoot
    $kitMan = Read-KV (Join-Path $src 'data\manifest.txt')
    if (-not $kitMan['mod_version']) { Say 'ไม่พบโฟลเดอร์ data: แตกไฟล์ zip ทั้งหมดก่อน แล้วรันจากโฟลเดอร์ที่แตกออกมา' 'Red'; $script:ExitCode = 1; return }
    $game = Find-Game -Ask
    if (-not $game) { Say 'ยกเลิก: ไม่ได้ระบุโฟลเดอร์เกม' 'Red'; $script:ExitCode = 1; return }
    Say "พบเกมที่: $game"
    Say "ม็อดเวอร์ชัน: $($kitMan['mod_version'])  (สร้างสำหรับเกมเวอร์ชัน $($kitMan['game_build']))"

    $oldMan = Read-KV (Join-Path $DataDir 'manifest.txt')
    $orig = Get-GameOrig $game $oldMan
    if (-not (Test-Compatible $orig $kitMan)) {
        Say 'ตรวจเวอร์ชันเกม...  ไม่ตรงกับม็อดชุดนี้ (เกมอาจอัปเดตแล้ว)' 'Red'
        Say 'ไม่ได้แก้ไขไฟล์ใด ๆ: โหลดม็อดเวอร์ชันล่าสุดมาติดตั้งแทน' 'Yellow'
        $script:ExitCode = 1; return
    }
    Say 'ตรวจเวอร์ชันเกม...  ตรงกับม็อด' 'Green'

    # คัดลอกชุดม็อดไปเก็บไว้ที่ %LOCALAPPDATA%\WWM-Thai (ลบโฟลเดอร์ที่แตก zip ทิ้งได้หลังติดตั้ง)
    $same = (Resolve-Path -LiteralPath $src).Path.TrimEnd('\') -eq (Resolve-Path -LiteralPath $ModHome).Path.TrimEnd('\')
    if (-not $same) {
        foreach ($n in 'wwm-thai.ps1', 'play.bat', 'uninstall.bat', 'README.txt') {
            $p = Join-Path $src $n
            if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination $ModHome -Force }
        }
        $man = Use-Kit $game $oldMan (Join-Path $src 'data')
        Get-ChildItem -LiteralPath $ModHome -Recurse -File | Unblock-File
    } else {
        Install-Data $game $kitMan $DataDir
        $man = $kitMan
    }
    $st = Read-KV $StateFile; $st['game_path'] = $game; Write-KV $StateFile $st
    Say "สำรองไฟล์ต้นฉบับไว้ที่: $BackupDir"
    Say "ติดตั้งสำเร็จ! (ม็อด $($man['mod_version'])) เข้าเกมแล้วตั้งภาษาเป็น ไทย" 'Green'
    Show-LaunchOption
}

function Main-Play {
    $game = $GameExe
    for ($i = 0; $i -lt 4; $i++) { $game = Split-Path $game }   # ...\Engine\Binaries\Win64r\wwm.exe -> โฟลเดอร์เกม
    if (-not (Test-Game $game)) { Say "ไม่พบไฟล์ภาษาของเกมที่ '$game': ข้ามม็อด" 'Yellow'; return }
    $st = Read-KV $StateFile; $st['game_path'] = $game
    $man = Read-KV (Join-Path $DataDir 'manifest.txt')
    if (-not $man['mod_version']) { Say 'ยังไม่ได้ติดตั้งม็อด (รัน install.bat ก่อน): เปิดเกมตามปกติ' 'Yellow'; return }
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
    $man = Read-KV (Join-Path $DataDir 'manifest.txt')
    if (-not (Restore-Original $game $man)) {
        Say 'คืนไฟล์บางไฟล์ไม่ได้: ใช้ Steam > คลิกขวาที่เกม > Properties > Installed Files > Verify integrity of game files' 'Yellow'
        $script:ExitCode = 1
    } else {
        Say 'คืนไฟล์ภาษาไทยต้นฉบับของเกมแล้ว' 'Green'
    }
    Say ''
    Say 'อย่าลืม: ลบบรรทัด play.bat ออกจาก Steam > Properties > Launch Options' 'Cyan'
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
