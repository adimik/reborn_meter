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
        
        # Stáhnout nový EXE
        response = requests.get(download_url, timeout=30)
        if response.status_code != 200:
            print(f"Chyba stahování: {response.status_code}")
            return
        
        # Zálohovat starý EXE
        backup_path = old_exe_path + ".backup"
        if os.path.exists(old_exe_path):
            shutil.copy2(old_exe_path, backup_path)
        
        # Zapsat nový EXE
        with open(old_exe_path, 'wb') as f:
            f.write(response.content)
        
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
