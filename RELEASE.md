# HP Monitor - EXE Build a Release

## Jak vytvořit novou verzi:

### 1. Změň verzi v kódu
```python
# V hp_monitor.py
VERSION = "1.0.1"  # Změň číslo
```

### 2. Build EXE
```bash
build.bat
```
Vytvoří:
- `dist/HPMonitor.exe`
- `dist/updater.exe`

### 3. Vytvoř GitHub Release

1. Jdi na: https://github.com/adimik/reborn_meter/releases/new

2. Vyplň:
   - **Tag version**: `v1.0.1` (s "v" na začátku!)
   - **Release title**: `HP Monitor v1.0.1`
   - **Description**: Co je nového

3. Nahraj soubory (Attach binaries):
   - `HPMonitor.exe`
   - `updater.exe` (volitelné, pro uživatele co už mají starou verzi)

4. Klikni **Publish release**

### 4. Hotovo!
Všichni uživatelé dostanou při příštím spuštění nabídku update.

## Pro distribuci nové instalace

Zabal do ZIP:
- `HPMonitor.exe`
- `updater.exe`
- `105937-OMRBGM-772.jpg`
- `uninstall.bat`

Kamarád rozbalí a spustí `HPMonitor.exe`.

## Důležité
- **Tag musí být formát**: `v1.0.0`, `v1.0.1` atd. (s "v"!)
- **EXE musí být jméno**: `HPMonitor.exe` (přesně)
- Verze v kódu MUSÍ odpovídat tagu (bez "v"): `1.0.1`
