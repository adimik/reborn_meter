# Auto Release Script
# Automaticky buildne, zvýší verzi a pushne na GitHub

Write-Host "=== Auto Release Script ===" -ForegroundColor Cyan
Write-Host ""

# 1. Načíst aktuální verzi z hp_monitor.py
$content = Get-Content "hp_monitor.py" -Raw
if ($content -match 'VERSION = "(\d+)\.(\d+)\.(\d+)"') {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    $patch = [int]$matches[3]
    
    $currentVersion = "$major.$minor.$patch"
    Write-Host "Aktuální verze: $currentVersion" -ForegroundColor Yellow
    
    # 2. Zvýšit patch verzi
    $newPatch = $patch + 1
    $newVersion = "$major.$minor.$newPatch"
    Write-Host "Nová verze: $newVersion" -ForegroundColor Green
    Write-Host ""
    
    # 3. Zapsat novou verzi do hp_monitor.py
    $newContent = $content -replace 'VERSION = "\d+\.\d+\.\d+"', "VERSION = `"$newVersion`""
    Set-Content "hp_monitor.py" -Value $newContent -NoNewline
    Write-Host "[1/5] Verze změněna na $newVersion" -ForegroundColor Green
    
} else {
    Write-Host "CHYBA: Nelze najít VERSION v hp_monitor.py" -ForegroundColor Red
    exit 1
}

# 4. Spustit build
Write-Host "[2/5] Spouštím build..." -ForegroundColor Cyan
& .\build.bat
if ($LASTEXITCODE -ne 0) {
    Write-Host "CHYBA: Build selhal!" -ForegroundColor Red
    exit 1
}
Write-Host "[2/5] Build dokončen" -ForegroundColor Green

# 5. Zkontrolovat, že EXE existuje
if (-not (Test-Path "dist\HPMonitor.exe")) {
    Write-Host "CHYBA: dist\HPMonitor.exe neexistuje!" -ForegroundColor Red
    exit 1
}
Write-Host "[3/5] EXE soubor vytvořen" -ForegroundColor Green

# 6. Git commit a push (všechny změny)
Write-Host "[4/5] Commitování všech změn..." -ForegroundColor Cyan
git add .
git commit -m "Release v$newVersion"
if ($LASTEXITCODE -ne 0) {
    Write-Host "CHYBA: Commit selhal!" -ForegroundColor Red
    exit 1
}

Write-Host "[5/5] Pushování na GitHub..." -ForegroundColor Cyan
git push origin HEAD:main
if ($LASTEXITCODE -ne 0) {
    Write-Host "CHYBA: Push selhal!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== HOTOVO! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Verze: v$newVersion" -ForegroundColor Yellow
Write-Host "EXE: dist\HPMonitor.exe" -ForegroundColor Yellow
Write-Host ""
Write-Host "DALŠÍ KROK (RUČNÍ):" -ForegroundColor Cyan
Write-Host "1. Jdi na: https://github.com/adimik/reborn_meter/releases/new" -ForegroundColor White
Write-Host "2. Tag: v$newVersion" -ForegroundColor White
Write-Host "3. Nahraj soubor: dist\HPMonitor.exe" -ForegroundColor White
Write-Host "4. Klikni 'Publish release'" -ForegroundColor White
Write-Host ""
