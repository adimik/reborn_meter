# HP Monitor Overlay

Overlay aplikace pro sledování HP v herním prostředí s Discord notifikacemi.

## Funkce

- 🎮 **Transparentní overlay** - Okno vždy nahoře, neruší hraní
- 📍 **Automatická detekce pozice** - Vyber oblast HP baru jedním kliknutím
- 🔄 **Pravidelný monitoring** - Kontrola každých 5 sekund
- 📊 **Dvojí detekce HP**:
  - OCR (Optical Character Recognition) pro čtení čísel
  - Detekce podle barvy HP baru
- 🔔 **Discord notifikace** - Upozornění když HP klesne na 0
- 💾 **Uložení nastavení** - Pozice a webhook se ukládají

## Instalace

### 1. Nainstaluj Python závislosti

```bash
pip install -r requirements.txt
```

### 2. Nainstaluj Tesseract OCR

**Windows:**
- Stáhni z: https://github.com/UB-Mannheim/tesseract/wiki
- Nainstaluj (například do `C:\Program Files\Tesseract-OCR`)
- Přidej do PATH nebo nastav cestu v kódu:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

## Použití

### 1. Spuštění aplikace

```bash
python hp_monitor.py
```

### 2. Nastavení Discord Webhooku

1. V Discordu, jdi do nastavení serveru → Integrace → Webhooks
2. Vytvoř nový webhook
3. Zkopíruj webhook URL
4. Vlož ho do pole "Discord Webhook URL" v aplikaci

### 3. Výběr HP oblasti

1. Klikni na tlačítko **"Vybrat HP Oblast"**
2. Aplikace se minimalizuje a zobrazí se selection tool
3. Klikni a táhni myší přes oblast kde se zobrazuje HP
4. Pusť tlačítko myši pro potvrzení výběru

### 4. Spuštění monitoringu

1. Klikni na **"Spustit Monitoring"**
2. Aplikace začne kontrolovat HP každých 5 sekund
3. Když HP klesne na 0, pošle se Discord notifikace

### 5. Uložení konfigurace

- Klikni na **"Uložit Konfiguraci"** pro uložení nastavení
- Při příštím spuštění se automaticky načte

## Tipy

- Pro nejlepší výsledky OCR vyber oblast pouze s číslem HP
- Pokud OCR nefunguje dobře, aplikace se pokusí detekovat HP podle červené barvy
- Overlay můžeš přesunout kamkoliv na obrazovku
- Pro zastavení monitoringu klikni znovu na tlačítko

## Řešení problémů

### OCR nečte čísla správně
- Zkontroluj že je Tesseract správně nainstalovaný
- Vyber větší/menší oblast HP baru
- Ujisti se že je text HP dostatečně kontrastní

### Discord notifikace nefungují
- Zkontroluj že je webhook URL správná
- Zkontroluj že máš přístup k internetu
- Webhook musí začínat `https://discord.com/api/webhooks/`

### Aplikace nezachytává správné HP
- Zkus vybrat jen oblast s číslem
- Pokud hra používá speciální font, může OCR selhat
- V takovém případě aplikace použije detekci podle barvy
