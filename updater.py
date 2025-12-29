import sys
import os
import time
import requests
import subprocess
import shutil

def update():
    """Stáhne nový EXE a nahradí starý"""
    print("Stahuji novou verzi...")
    
    # URL nového EXE z příkazové řádky
    if len(sys.argv) < 3:
        print("Chyba: Nedostatek parametrů")
        return
    
    download_url = sys.argv[1]
    old_exe_path = sys.argv[2]
    
    try:
        # Počkat až se zavře hlavní aplikace
        time.sleep(2)
        
        # Stáhnout nový EXE s progress barem
        print("\nStahuji novou verzi...")
        response = requests.get(download_url, stream=True, timeout=30)
        if response.status_code != 200:
            print(f"Chyba stahování: {response.status_code}")
            return
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 KB
        downloaded = 0
        
        # Dočasný soubor
        temp_path = old_exe_path + ".download"
        
        with open(temp_path, 'wb') as f:
            for data in response.iter_content(block_size):
                downloaded += len(data)
                f.write(data)
                
                # Progress bar
                if total_size > 0:
                    percent = int((downloaded / total_size) * 100)
                    bar_length = 50
                    filled = int((downloaded / total_size) * bar_length)
                    bar = '=' * filled + '-' * (bar_length - filled)
                    size_mb = downloaded / 1024 / 1024
                    total_mb = total_size / 1024 / 1024
                    print(f'\r[{bar}] {percent}% ({size_mb:.1f}/{total_mb:.1f} MB)', end='', flush=True)
        
        print("\n")
        
        # Zálohovat starý EXE
        backup_path = old_exe_path + ".backup"
        if os.path.exists(old_exe_path):
            print("Zálohuji starou verzi...")
            shutil.copy2(old_exe_path, backup_path)
        
        # Přesunout stažený soubor
        print("Instaluji novou verzi...")
        shutil.move(temp_path, old_exe_path)
        
        print("Aktualizace dokončena! Restartuji...")
        time.sleep(1)
        
        # Spustit novou verzi
        subprocess.Popen([old_exe_path])
        
        # Smazat zálohu
        if os.path.exists(backup_path):
            time.sleep(2)
            try:
                os.remove(backup_path)
            except:
                pass
                
    except Exception as e:
        print(f"Chyba při aktualizaci: {e}")
        # Obnovit ze zálohy
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, old_exe_path)
        input("Stiskni Enter...")

if __name__ == "__main__":
    update()
