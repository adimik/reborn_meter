import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
from PIL import ImageGrab, Image, ImageTk
import requests
import json
import threading
import time
from datetime import datetime
import os
import sys
import subprocess
import ctypes

VERSION = "1.0.2"
UPDATE_URL = "https://api.github.com/repos/adimik/reborn_meter/releases/latest"
DEPRECATED_URL = "https://raw.githubusercontent.com/adimik/reborn_meter/main/deprecated.txt"

try:
    import pytesseract
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Tesseract-OCR\tesseract.exe',
    ]
    
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
    
    TESSERACT_AVAILABLE = True
except Exception as e:
    print(f"Tesseract není dostupný: {e}")
    TESSERACT_AVAILABLE = False

class HPMonitorOverlay:
    def __init__(self):
        # Vytvořit root window nejdřív (potřebné pro messagebox)
        self.root = tk.Tk()
        self.root.withdraw()  # Skrýt dokud není zkontrolovaná verze
        
        # Kontrola aktualizací při startu
        self.check_for_updates()
        
        # Zobrazit okno
        self.root.deiconify()
        self.root.title("System Monitor")
        
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        
        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        
        self.monitoring = False
        self.hp_position = None
        self.last_hp = None
        self.last_valid_hp = None
        self.selecting_area = False
        self.discord_webhook = ""
        self.discord_user_id = ""
        self.compact_mode = False
        self.expanded_mode = False
        
        # Načtení ikonky pro compact mód
        self.icon_image = None
        self.icon_photo = None
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "105937-OMRBGM-772.jpg")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = img.resize((80, 80), Image.Resampling.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Nelze načíst ikonu: {e}")
        
        self.load_config()
        self.setup_ui()
        self.setup_drag()
        
        # Nastavit overlay aby nekradl focus od hry - musí být až PO setup_ui
        self.set_no_activate()
    
    def setup_drag(self):
        def start_drag(event):
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.drag_data["dragging"] = True
        
        def do_drag(event):
            if self.drag_data["dragging"]:
                x = self.root.winfo_x() + (event.x - self.drag_data["x"])
                y = self.root.winfo_y() + (event.y - self.drag_data["y"])
                self.root.geometry(f"+{x}+{y}")
        
        def stop_drag(event):
            self.drag_data["dragging"] = False
        
        self.title_bar.bind("<Button-1>", start_drag)
        self.title_bar.bind("<B1-Motion>", do_drag)
        self.title_bar.bind("<ButtonRelease-1>", stop_drag)
        
        self.title_label.bind("<Button-1>", start_drag)
        self.title_label.bind("<B1-Motion>", do_drag)
        self.title_label.bind("<ButtonRelease-1>", stop_drag)
    
    def set_no_activate(self):
        """Nastaví okno aby nekradlo focus od hry"""
        self.root.update_idletasks()
        
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        if not hwnd:
            hwnd = self.root.winfo_id()
        
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_NOACTIVATE
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    
    def is_game_focused(self):
        """Zkontroluje jestli je hra na popředí (aktivní okno)"""
        try:
            # Získat aktivní okno
            foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
            
            # Získat název okna
            length = ctypes.windll.user32.GetWindowTextLengthW(foreground_hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(foreground_hwnd, buff, length + 1)
            window_title = buff.value.lower()
            
            # Kontrola jestli je to overlay (náš program) - pokud ano, považuj to za OK
            if 'system monitor' in window_title or 'hp monitor' in window_title:
                return True
            
            # PRIORITNÍ: Přesné jméno hry
            if 'lineage' in window_title:
                return True
            
            # Seznam běžných herních klíčových slov v názvech oken
            # Pokud není overlay, zkontroluj jestli obsahuje herní klíčová slova
            game_keywords = ['game', 'hra', 'metin', 'wow', 'league', 'dota', 
                           'steam', 'epic', 'unity', 'unreal', 'directx', 'dx11', 'dx12',
                           'fullscreen', 'opengl', 'vulkan']
            
            # Pokud je prázdný název nebo známý ne-herní program, vrať False
            non_game = ['explorer', 'chrome', 'firefox', 'edge', 'discord', 
                       'spotify', 'notepad', 'code', 'visual studio', 'file explorer',
                       'dokumenty', 'documents', 'this pc', 'tento počítač']
            
            for ng in non_game:
                if ng in window_title:
                    return False
            
            # Pokud obsahuje herní klíčové slovo, považuj za hru
            for keyword in game_keywords:
                if keyword in window_title:
                    return True
            
            # Pokud má okno název, pravděpodobně to je hra (fallback)
            # Prázdný název = desktop
            return len(window_title) > 0
            
        except Exception as e:
            print(f"Chyba detekce okna: {e}")
            return True  # Při chybě raději pokračuj v monitoringu
    
    def setup_ui(self):
        self.root.configure(bg='#0a0a0a')
        self.root.geometry("400x550")
        self.root.resizable(False, False)
        
        main_container = tk.Frame(self.root, bg='#1a1a1a', highlightthickness=0, highlightbackground='#333333')
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        self.title_bar = tk.Frame(main_container, bg='#252525', height=35)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        self.title_bar.pack_propagate(False)
        
        self.title_label = tk.Label(self.title_bar, text="⚡ HP Monitor", 
                                     bg='#252525', fg='#00ff88', 
                                     font=('Segoe UI', 10, 'bold'))
        self.title_label.pack(side=tk.LEFT, padx=10)
        
        close_btn = tk.Label(self.title_bar, text="✕", bg='#252525', fg='#ffffff', 
                            font=('Segoe UI', 12), cursor='hand2', padx=15)
        close_btn.pack(side=tk.RIGHT)
        
        def close_click(e):
            self.root.quit()
            return "break"
        
        close_btn.bind("<Button-1>", close_click)
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg='#ff4444'))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg='#252525'))
        
        # Expand button (rozbalení pro další features)
        self.expand_btn = tk.Label(self.title_bar, text="▼", bg='#252525', fg='#888888', 
                                   font=('Segoe UI', 10), cursor='hand2', padx=15)
        self.expand_btn.pack(side=tk.RIGHT)
        
        def expand_click(e):
            self.toggle_expanded_mode()
            return "break"
        
        self.expand_btn.bind("<Button-1>", expand_click)
        self.expand_btn.bind("<Enter>", lambda e: self.expand_btn.config(bg='#3e3e42'))
        self.expand_btn.bind("<Leave>", lambda e: self.expand_btn.config(bg='#252525'))
        
        # Minimize button
        min_btn = tk.Label(self.title_bar, text="◀", bg='#252525', fg='#ffffff', 
                          font=('Segoe UI', 10), cursor='hand2', padx=15)
        min_btn.pack(side=tk.RIGHT)
        
        def min_click(e):
            self.toggle_compact_mode()
            return "break"
        
        min_btn.bind("<Button-1>", min_click)
        min_btn.bind("<Enter>", lambda e: min_btn.config(bg='#3e3e42'))
        min_btn.bind("<Leave>", lambda e: min_btn.config(bg='#252525'))
        
        content_frame = tk.Frame(main_container, bg='#1a1a1a', padx=15, pady=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Uložení referencí pro správné přepínání
        self.main_container = main_container
        self.content_frame = content_frame
        
        self.full_frame = tk.Frame(content_frame, bg='#1a1a1a')
        self.full_frame.pack(fill=tk.BOTH, expand=True)
        
        webhook_label = tk.Label(self.full_frame, text="Discord Webhook", 
                                bg='#1a1a1a', fg='#888888', 
                                font=('Segoe UI', 9))
        webhook_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0,5))
        
        # Webhook help button vedle labelu
        webhook_help_btn = tk.Label(self.full_frame, text="❓", bg='#2d2d30', fg='#888888',
                                    font=('Segoe UI', 10), cursor='hand2', width=3, takefocus=0)
        webhook_help_btn.grid(row=0, column=2, sticky=tk.E, pady=(0,5))
        
        def webhook_help_click(e):
            self.show_webhook_help(webhook_help_btn)
            return "break"
        
        webhook_help_btn.bind("<Button-1>", webhook_help_click)
        webhook_help_btn.bind("<Enter>", lambda e: webhook_help_btn.config(bg='#3e3e42'))
        
        self.webhook_entry = tk.Entry(self.full_frame, bg='#1e1e1e', fg='#888888', 
                                       font=('Segoe UI', 9), relief=tk.FLAT, 
                                       insertbackground='#888888', bd=0, state='readonly', 
                                       readonlybackground='#1e1e1e')
        self.webhook_entry.grid(row=1, column=0, columnspan=2, sticky='ew', ipady=5, pady=(0,10), padx=(0,2))
        # Nastavit hodnotu před readonly
        self.webhook_entry.config(state='normal')
        self.webhook_entry.insert(0, self.discord_webhook)
        self.webhook_entry.config(state='readonly')
        
        webhook_paste_btn = tk.Label(self.full_frame, text="📋", bg='#2d2d30', fg='#888888',
                                     font=('Segoe UI', 10), cursor='hand2', width=3)
        webhook_paste_btn.grid(row=1, column=2, sticky=tk.E, pady=(0,10))
        
        def webhook_paste_click(e):
            self.paste_to_entry(self.webhook_entry)
            return "break"
        
        webhook_paste_btn.bind("<Button-1>", webhook_paste_click)
        webhook_paste_btn.bind("<Enter>", lambda e: webhook_paste_btn.config(bg='#3e3e42'))
        webhook_paste_btn.bind("<Leave>", lambda e: webhook_paste_btn.config(bg='#2d2d30'))
        
        user_id_label = tk.Label(self.full_frame, text="Discord User ID (číselné ID, ne nick!)", 
                                bg='#1a1a1a', fg='#888888', 
                                font=('Segoe UI', 9))
        user_id_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0,5))
        
        # User ID help button
        user_id_help_btn = tk.Label(self.full_frame, text="❓", bg='#2d2d30', fg='#888888',
                                    font=('Segoe UI', 10), cursor='hand2', width=3, takefocus=0)
        user_id_help_btn.grid(row=2, column=2, sticky=tk.E, pady=(0,5))
        
        def user_id_help_click(e):
            self.show_user_id_help(user_id_help_btn)
            return "break"
        
        user_id_help_btn.bind("<Button-1>", user_id_help_click)
        user_id_help_btn.bind("<Enter>", lambda e: user_id_help_btn.config(bg='#3e3e42'))
        
        self.user_id_entry = tk.Entry(self.full_frame, bg='#1e1e1e', fg='#888888', 
                                       font=('Segoe UI', 9), relief=tk.FLAT, 
                                       insertbackground='#888888', bd=0, state='readonly', 
                                       readonlybackground='#1e1e1e')
        self.user_id_entry.grid(row=3, column=0, columnspan=2, sticky='ew', ipady=5, pady=(0,15), padx=(0,2))
        # Nastavit hodnotu před readonly
        self.user_id_entry.config(state='normal')
        self.user_id_entry.insert(0, self.discord_user_id)
        self.user_id_entry.config(state='readonly')
        
        user_id_paste_btn = tk.Label(self.full_frame, text="📋", bg='#2d2d30', fg='#888888',
                                     font=('Segoe UI', 10), cursor='hand2', width=3)
        user_id_paste_btn.grid(row=3, column=2, sticky=tk.E, pady=(0,15))
        
        def user_id_paste_click(e):
            self.paste_to_entry(self.user_id_entry)
            return "break"
        
        user_id_paste_btn.bind("<Button-1>", user_id_paste_click)
        user_id_paste_btn.bind("<Enter>", lambda e: user_id_paste_btn.config(bg='#3e3e42'))
        user_id_paste_btn.bind("<Leave>", lambda e: user_id_paste_btn.config(bg='#2d2d30'))
        
        # Vybrat Oblast button
        select_btn = tk.Label(self.full_frame, text="📍 Vybrat Oblast", bg='#2d2d30', fg='#ffffff',
                             font=('Segoe UI', 9, 'bold'), cursor='hand2', 
                             relief=tk.FLAT, padx=10, pady=10)
        select_btn.grid(row=4, column=0, sticky='ew', padx=5)
        
        def select_area_click(e):
            self.start_area_selection()
            return "break"
        
        select_btn.bind("<Button-1>", select_area_click)
        select_btn.bind("<Enter>", lambda e: select_btn.config(bg='#3e3e42'))
        select_btn.bind("<Leave>", lambda e: select_btn.config(bg='#2d2d30'))
        
        # Spustit button
        self.monitor_btn = tk.Label(self.full_frame, text="▶️ Spustit", bg='#007acc', fg='#ffffff',
                                    font=('Segoe UI', 9, 'bold'), cursor='hand2', 
                                    relief=tk.FLAT, padx=10, pady=10)
        self.monitor_btn.grid(row=4, column=1, sticky='ew', padx=5)
        
        def monitor_click(e):
            self.toggle_monitoring()
            return "break"
        
        self.monitor_btn.bind("<Button-1>", monitor_click)
        self.monitor_btn.bind("<Enter>", lambda e: self.monitor_btn.config(bg='#3e3e42'))
        self.monitor_btn.bind("<Leave>", lambda e: self.monitor_btn.config(bg='#007acc'))
        
        # Uložit button
        save_btn = tk.Label(self.full_frame, text="💾 Uložit", bg='#2d2d30', fg='#ffffff',
                           font=('Segoe UI', 9, 'bold'), cursor='hand2', 
                           relief=tk.FLAT, padx=10, pady=10)
        save_btn.grid(row=4, column=2, sticky='ew', padx=5)
        
        def save_click(e):
            self.save_config()
            return "break"
        
        save_btn.bind("<Button-1>", save_click)
        save_btn.bind("<Enter>", lambda e: save_btn.config(bg='#3e3e42'))
        save_btn.bind("<Leave>", lambda e: save_btn.config(bg='#2d2d30'))
        
        self.full_frame.columnconfigure(0, weight=1)
        self.full_frame.columnconfigure(1, weight=1)
        self.full_frame.columnconfigure(2, weight=1)
        
        test_frame = tk.Frame(self.full_frame, bg='#1a1a1a')
        test_frame.grid(row=5, column=0, columnspan=3, pady=(15,0), sticky='ew')
        
        test_label = tk.Label(test_frame, text="Testy", bg='#1a1a1a', fg='#888888',
                             font=('Segoe UI', 9))
        test_label.pack(side=tk.LEFT)
        
        test_buttons = [
            ("🧪 Test", self.test_webhook)
        ]
        
        for text, command in test_buttons:
            btn = tk.Label(test_frame, text=text, bg='#2d2d30', fg='#888888',
                          font=('Segoe UI', 8), cursor='hand2', padx=8, pady=4)
            btn.pack(side=tk.LEFT, padx=5)
            
            def make_test_handler(cmd):
                def handler(e):
                    cmd()
                    return "break"
                return handler
            
            btn.bind("<Button-1>", make_test_handler(command))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg='#3e3e42'))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg='#2d2d30'))
        
        status_frame = tk.Frame(self.full_frame, bg='#252525', pady=10, padx=15)
        status_frame.grid(row=6, column=0, columnspan=3, sticky='ew', pady=(15,0))
        
        status_text = "✓ Připraven"
        if not TESSERACT_AVAILABLE:
            status_text = "✓ Připraven (detekce barvy)"
        
        self.status_label = tk.Label(status_frame, text=status_text, 
                                     bg='#252525', fg='#00ff88',
                                     font=('Segoe UI', 9))
        self.status_label.pack()
        
        hp_frame = tk.Frame(self.full_frame, bg='#0d0d0d', pady=20)
        hp_frame.grid(row=7, column=0, columnspan=3, sticky='ew', pady=(15,0))
        
        hp_label_text = tk.Label(hp_frame, text="HP", bg='#0d0d0d', fg='#555555',
                                font=('Segoe UI', 10))
        hp_label_text.pack()
        
        self.hp_label = tk.Label(hp_frame, text="N/A", bg='#0d0d0d', fg='#00ff88',
                                font=('Segoe UI', 20, 'bold'))
        self.hp_label.pack()
        
        self.position_label = tk.Label(self.full_frame, text="Pozice HP: Nevybráno",
                                      bg='#1a1a1a', fg='#555555',
                                      font=('Segoe UI', 8))
        self.position_label.grid(row=8, column=0, columnspan=3, pady=(10,0))
        
        if self.hp_position:
            self.position_label.config(text=f"Pozice: X:{self.hp_position[0]} Y:{self.hp_position[1]} W:{self.hp_position[2]} H:{self.hp_position[3]}")
        
        # Compact frame - přímo v main_container, bez jakýchkoliv okrajů
        self.compact_frame = tk.Frame(self.main_container, bg='#0a0a0a', bd=0, highlightthickness=0)
        
        if self.icon_photo:
            self.compact_icon_btn = tk.Label(self.compact_frame, image=self.icon_photo, 
                                            bg='#0a0a0a', cursor='hand2', bd=0, highlightthickness=0)
            self.compact_icon_btn.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            self.compact_icon_btn.bind("<Button-1>", self.on_compact_click)
            self.compact_icon_btn.bind("<B1-Motion>", self.drag_compact_window)
            self.compact_icon_btn.bind("<ButtonRelease-1>", self.on_compact_release)
        else:
            # Fallback pokud se ikona nenačte
            fallback_btn = tk.Label(self.compact_frame, text="⚡", bg='#0a0a0a', fg='#00ff88',
                                   font=('Segoe UI', 40), cursor='hand2', bd=0, highlightthickness=0)
            fallback_btn.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            fallback_btn.bind("<Button-1>", self.on_compact_click)
            fallback_btn.bind("<B1-Motion>", self.drag_compact_window)
            fallback_btn.bind("<ButtonRelease-1>", self.on_compact_release)
    
    def paste_to_entry(self, entry_widget):
        """Vloží obsah schránky do vstupního pole"""
        try:
            clipboard_text = self.root.clipboard_get()
            # Dočasně povolit editaci
            entry_widget.config(state='normal')
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, clipboard_text)
            # Zase zakázat editaci
            entry_widget.config(state='readonly')
        except tk.TclError:
            # Schránka je prázdná nebo obsahuje nepoužitelná data
            entry_widget.config(state='readonly')
            pass
    
    def show_user_id_help(self, button):
        """Zobrazí návod jak získat User ID"""
        help_text = """Jak získat své Discord User ID:

1. V Discordu otevři Nastavení
2. Jdi do: Pokročilé (Advanced)
3. Zapni: Režim vývojáře (Developer Mode)
4. Zavři nastavení
5. Levé tlačítko na svůj nick/avatar
6. Tlačítko: Copy User ID
7. Vlož sem (bude to dlouhé číslo)

Příklad: 123456789012345678

Toto NENÍ nick (např. "JohnDoe"), ale číselné ID!"""
        
        self.show_tooltip_popup(help_text, "Jak získat User ID", button)
    
    def show_webhook_help(self, button):
        """Zobrazí návod jak vytvořit Discord webhook"""
        help_text = """Jak vytvořit Discord webhook:

1. Otevři Discord server (musíš mít oprávnění)
2. Klikni pravým na kanál kam chceš notifikace
3. Upravit kanál → Integrace
4. Vytvořit webhook (Create Webhook)
5. Pojmenuj si ho (např. "HP Monitor")
6. Zkopíruj Webhook URL
7. Vlož sem

URL vypadá takto:
https://discord.com/api/webhooks/123.../abc...

Webhook posílá zprávy do zvoleného kanálu!"""
        
        self.show_tooltip_popup(help_text, "Jak vytvořit Webhook", button)
    
    def show_tooltip_popup(self, text, title, button):
        """Vytvoří vlastní popup tooltip bez zvuku"""
        # Pokud už existuje popup pro toto tlačítko, zavři ho
        if hasattr(button, '_active_popup') and button._active_popup:
            try:
                button._active_popup.destroy()
            except:
                pass
            button._active_popup = None
            # Obnovit původní Leave binding
            button.bind("<Leave>", lambda e: button.config(bg='#2d2d30'))
            return
        
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.configure(bg='#2d2d30')
        popup.overrideredirect(True)
        
        # Vždy navrchu jako overlay
        popup.attributes('-topmost', True)
        popup.attributes('-alpha', 0.98)
        
        # Pozice vedle myši
        x = self.root.winfo_pointerx() + 10
        y = self.root.winfo_pointery() + 10
        popup.geometry(f"+{x}+{y}")
        
        # Frame s borderem (vytvoř UI před aplikací WS_EX_NOACTIVATE)
        border_frame = tk.Frame(popup, bg='#888888', padx=2, pady=2)
        border_frame.pack(fill=tk.BOTH, expand=True)
        
        content_frame = tk.Frame(border_frame, bg='#2d2d30', padx=15, pady=10)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titulek
        title_label = tk.Label(content_frame, text=title, 
                              bg='#2d2d30', fg='#ffffff',
                              font=('Segoe UI', 11, 'bold'))
        title_label.pack(anchor='w', pady=(0,8))
        
        # Text
        text_label = tk.Label(content_frame, text=text, 
                            bg='#2d2d30', fg='#cccccc',
                            font=('Segoe UI', 9), justify=tk.LEFT)
        text_label.pack(anchor='w')
        
        # Zajistit aby popup nebral focus (po vytvoření UI)
        popup.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(popup.winfo_id())
        if not hwnd:
            hwnd = popup.winfo_id()
        
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_NOACTIVATE
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        # Uložit referenci na popup k tlačítku
        button._active_popup = popup
        
        # Zavřít popup při opuštění tlačítka
        def close_on_leave(event=None):
            try:
                popup.destroy()
            except:
                pass
            button._active_popup = None
            # Obnovit původní Leave binding (reset barvy)
            button.bind("<Leave>", lambda e: button.config(bg='#2d2d30'))
            button.config(bg='#2d2d30')
        
        # Přebindovat Leave na tlačítku
        button.bind("<Leave>", close_on_leave)
        
        # Zavřít i při kliku na popup
        popup.bind('<Button-1>', lambda e: close_on_leave())
        
        # Zobrazit popup bez brání focusu
        popup.lift()
    
    def toggle_expanded_mode(self):
        """Přepne mezi normálním a expandovaným módem"""
        self.expanded_mode = not self.expanded_mode
        
        if self.expanded_mode:
            self.expand_btn.config(text="▲")
            self.root.geometry("400x750")
            self.show_expanded_features()
        else:
            self.expand_btn.config(text="▼")
            self.root.geometry("400x550")
            self.hide_expanded_features()
    
    def show_expanded_features(self):
        """Zobrazí expandovanou sekci pro další features"""
        if hasattr(self, 'expanded_frame'):
            self.expanded_frame.grid()
        else:
            self.expanded_frame = tk.Frame(self.full_frame, bg='#0d0d0d', pady=20)
            self.expanded_frame.grid(row=9, column=0, columnspan=3, sticky='nsew', pady=(15,0))
            
            label = tk.Label(self.expanded_frame, text="🔧 Ve vývoji", 
                           bg='#0d0d0d', fg='#555555',
                           font=('Segoe UI', 12))
            label.pack(pady=30)
            
            canvas_placeholder = tk.Frame(self.expanded_frame, bg='#1a1a1a', 
                                         height=100, width=350,
                                         highlightthickness=1, highlightbackground='#333333')
            canvas_placeholder.pack(pady=10)
            canvas_placeholder.pack_propagate(False)
            
            canvas_label = tk.Label(canvas_placeholder, text="Prostor pro další metery",
                                  bg='#1a1a1a', fg='#444444',
                                  font=('Segoe UI', 9, 'italic'))
            canvas_label.place(relx=0.5, rely=0.5, anchor='center')
    
    def hide_expanded_features(self):
        """Skryje expandovanou sekci"""
        if hasattr(self, 'expanded_frame'):
            self.expanded_frame.grid_remove()
    
    def on_compact_click(self, event):
        """Obslužení kliknutí na compact ikonku - ulož počáteční pozici"""
        self.compact_click_x = event.x
        self.compact_click_y = event.y
        self.compact_drag_started = False
    
    def drag_compact_window(self, event):
        """Přesouvání okna v compact módu"""
        # Pokud se myš pohnula více než 5 pixelů, začne se dragging
        if hasattr(self, 'compact_click_x'):
            dx = abs(event.x - self.compact_click_x)
            dy = abs(event.y - self.compact_click_y)
            if dx > 5 or dy > 5:
                self.compact_drag_started = True
        
        if getattr(self, 'compact_drag_started', False):
            x = self.root.winfo_x() + event.x - 40  # 40 je polovička šířky ikony
            y = self.root.winfo_y() + event.y - 40
            self.root.geometry(f"+{x}+{y}")
        else:
            # Pokud se myš pohla jen málo, bude to kliknutí
            pass
    
    def on_compact_release(self, event):
        """Obslužení puštění tlačítka - pokud nedošlo k drag, toggle compact mode"""
        if not getattr(self, 'compact_drag_started', False):
            self.toggle_compact_mode()
        self.compact_drag_started = False
    
    def start_area_selection(self):
        self.root.withdraw()
        time.sleep(0.3)
        
        screenshot = ImageGrab.grab()
        
        self.selection_window = tk.Toplevel()
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-topmost', True)
        self.selection_window.attributes('-alpha', 0.3)
        
        self.canvas = tk.Canvas(self.selection_window, cursor="cross", bg='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.tk_image = ImageTk.PhotoImage(screenshot)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        
        self.rect = None
        self.start_x = None
        self.start_y = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
    
    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 
                                                  self.start_x, self.start_y, 
                                                  outline='red', width=2)
    
    def on_drag(self, event):
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)
    
    def on_release(self, event):
        end_x = event.x
        end_y = event.y
        
        x = min(self.start_x, end_x)
        y = min(self.start_y, end_y)
        w = abs(end_x - self.start_x)
        h = abs(end_y - self.start_y)
        
        self.hp_position = (int(x), int(y), int(w), int(h))
        
        self.selection_window.destroy()
        self.root.deiconify()
        
        self.position_label.config(text=f"Pozice: X:{x} Y:{y} W:{w} H:{h}")
        self.status_label.config(text="✓ Oblast vybrána", fg="#00ff88")
    
    def toggle_monitoring(self):
        if not self.monitoring:
            if not self.hp_position:
                messagebox.showerror("Chyba", "Nejprve vyberte HP oblast!")
                return
            
            self.discord_webhook = self.webhook_entry.get()
            self.discord_user_id = self.user_id_entry.get()
            if not self.discord_webhook:
                messagebox.showwarning("Varování", "Discord webhook URL není nastavena!")
            
            self.monitoring = True
            self.monitor_btn.config(text="⏸️ Zastavit", bg='#ff4444')
            self.status_label.config(text="✓ Monitorování aktivní", fg="#00ff88")
            
            self.monitor_thread = threading.Thread(target=self.monitor_hp, daemon=True)
            self.monitor_thread.start()
        else:
            self.monitoring = False
            self.monitor_btn.config(text="▶️ Spustit", bg='#007acc')
            self.status_label.config(text="⏹️ Monitorování zastaveno", fg="#ffa500")
    
    def monitor_hp(self):
        while self.monitoring:
            try:
                # PRVNÍ KONTROLA - před čekáním
                if not self.is_game_focused():
                    self.root.after(0, lambda: self.update_hp_display("⏸"))
                    self.root.after(0, lambda: self.set_hp_color("#ffa500"))
                    self.root.after(0, lambda: self.status_label.config(
                        text="⏸️ Hra není aktivní (pauza)", fg="#ffa500"))
                    time.sleep(2)  # Kratší čekání při pauze
                    continue
                
                # Čekat 5 sekund (ale během toho může uživatel přepnout okno!)
                time.sleep(5)
                
                # DRUHÁ KONTROLA - těsně před scanem (po 5 sekundách může být jiné okno!)
                if not self.is_game_focused():
                    print("⏸ Okno se změnilo během čekání - přeskakuji scan")
                    self.root.after(0, lambda: self.update_hp_display("⏸"))
                    self.root.after(0, lambda: self.set_hp_color("#ffa500"))
                    self.root.after(0, lambda: self.status_label.config(
                        text="⏸️ Hra není aktivní (pauza)", fg="#ffa500"))
                    continue
                
                hp_value = self.read_hp_value()
                
                if hp_value is None:
                    # OCR nenalezlo žádné číslo - NEPŘIDEJŽ last_valid_hp!
                    self.root.after(0, lambda: self.update_hp_display("---"))
                    self.root.after(0, lambda: self.set_hp_color("#808080"))
                    self.root.after(0, lambda: self.status_label.config(
                        text="⏸️ Čekám na herní okno...", fg="#ffa500"))
                else:
                    # OCR našlo platné HP
                    self.root.after(0, lambda v=hp_value: self.update_hp_display(v))
                    
                    # Poslat notifikaci JEN když OCR ÚspĚšNĚ našlo 0 A hra je stále aktivní
                    if hp_value == 0 and self.last_valid_hp and self.last_valid_hp > 0:
                        # TŘETÍ KONTROLA - zkontrolovat že hra je stále na popředí před odesláním
                        if self.is_game_focused():
                            self.send_discord_notification(hp_value)
                            self.root.after(0, lambda: self.set_hp_color("#ff4444"))
                            self.root.after(0, lambda: self.status_label.config(
                                text="⚠️ HP = 0! Alert odeslán!", fg="#ff4444"))
                        else:
                            print("HP=0 detekováno, ale hra není aktivní - notifikace NEBYLA odeslána")
                            self.root.after(0, lambda: self.status_label.config(
                                text="⏸️ Hra není aktivní (pauza)", fg="#ffa500"))
                    elif hp_value > 0:
                        self.root.after(0, lambda: self.set_hp_color("#00ff88"))
                        if self.status_label.cget("text") != "✓ Monitorování aktivní":
                            self.root.after(0, lambda: self.status_label.config(
                                text="✓ Monitorování aktivní", fg="#00ff88"))
                    
                    # Aktualizovat last_valid_hp JEN když OCR našlo platné HP
                    self.last_valid_hp = hp_value
                
                self.last_hp = hp_value
                
            except Exception as e:
                print(f"Chyba: {e}")
                self.root.after(0, lambda e=e: self.status_label.config(
                    text=f"❌ Chyba: {str(e)[:30]}", fg="#ff4444"))
    
    def read_hp_value(self):
        if not self.hp_position:
            return None
        
        x, y, w, h = self.hp_position
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        img_np = np.array(screenshot)
        img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # Validace že screenshot vypadá jako herní UI
        if not self.is_valid_screenshot(img_cv):
            return None
        
        # Extra validace - zkontrolovat že to nevypadá jako File Manager
        if self.looks_like_file_manager(img_cv):
            print("⚠ Screenshot vypadá jako File Manager - přeskakuji")
            return None
        
        if TESSERACT_AVAILABLE:
            try:
                # Zvětšení obrázku 6x pro maximální OCR přesnost
                img_large = cv2.resize(img_cv, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
                
                gray = cv2.cvtColor(img_large, cv2.COLOR_BGR2GRAY)
                
                # Velmi silný kontrast pro ostré číslice
                gray = cv2.convertScaleAbs(gray, alpha=2.5, beta=15)
                
                # Bilateral filter pro odstranění šumu
                gray = cv2.bilateralFilter(gray, 11, 90, 90)
                
                # Morphological opening pro odstranění malých artefaktů
                kernel = np.ones((2,2), np.uint8)
                gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
                
                # Threshold pro čistší text
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Uložit debug screenshot do aktuální složky (kde je EXE)
                if getattr(sys, 'frozen', False):
                    # Pokud je to EXE, ulož vedle EXE
                    debug_path = os.path.join(os.path.dirname(sys.executable), "debug_ocr.png")
                else:
                    # Pokud je to Python skript, ulož vedle skriptu
                    debug_path = os.path.join(os.path.dirname(__file__), "debug_ocr.png")
                cv2.imwrite(debug_path, thresh)
                print(f"Debug screenshot uložen: {debug_path}")
                
                # OCR s lepší konfigurací pro dlouhá čísla
                # psm 6 = uniform block of text, psm 7 = single line
                text = pytesseract.image_to_string(thresh, config='--psm 6 -c tessedit_char_whitelist=0123456789/')
                text = text.strip().replace(' ', '').replace('\n', '')  # Odstranit mezery a nové řádky
                
                print(f"OCR raw: '{text}'")  # Debug
                
                # Parse formátu "aktuální/maximum" - VYŽADOVAT lomítko!
                import re
                match = re.search(r'(\d+)/(\d+)', text)
                if match:
                    current_hp = int(match.group(1))
                    max_hp = int(match.group(2))
                    
                    # Validace: current HP nemůže být větší než max HP
                    if current_hp > max_hp:
                        print(f"⚠ Neplatné HP: {current_hp}/{max_hp} (current > max)")
                        return None
                    
                    # Validace: HP musí být rozumné číslo (ne 0/0)
                    if max_hp == 0:
                        print(f"⚠ Neplatné HP: {current_hp}/{max_hp} (max=0)")
                        return None
                    
                    print(f"✓ HP parsed: {current_hp}/{max_hp}")
                    return current_hp
                
                # BEZ fallbacku - pokud není správný formát, vrať None
                print(f"⚠ OCR nenašlo správný formát HP (číslo/číslo): '{text}'")
                return None
                    
            except Exception as e:
                print(f"OCR chyba: {e}")
        
        return self.detect_hp_by_color(img_cv)
    
    def looks_like_file_manager(self, img):
        """Detekuje jestli screenshot vypadá jako File Manager (bílé pozadí, málo barev)"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            
            # File Manager má obvykle světlé pozadí (>200), hra má tmavé (<100)
            if mean_brightness > 180:
                return True
            
            # Zkontrolovat pestrost barev - File Manager má méně barev než hra
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            saturation = hsv[:,:,1]
            mean_saturation = np.mean(saturation)
            
            # Nízká saturace = šedivé/bílé = pravděpodobně File Manager
            if mean_saturation < 30:
                return True
            
            return False
        except:
            return False
    
    def is_valid_screenshot(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        if mean_brightness < 10:
            return False
        
        variance = np.var(gray)
        if variance < 5:
            return False
        
        return True
    
    def detect_hp_by_color(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2
        
        red_pixels = cv2.countNonZero(mask)
        total_pixels = img.shape[0] * img.shape[1]
        
        if red_pixels / total_pixels < 0.05:
            return 0
        
        return int((red_pixels / total_pixels) * 100)
    
    def send_discord_notification(self, hp_value, is_test=False):
        if not self.discord_webhook:
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            title = "🧪 Test Alert!" if is_test else "⚠️ HP Alert!"
            description = "**Test notifikace - vše funguje!**" if is_test else f"**HP kleslo na {hp_value}!**"
            
            payload = {
                "embeds": [{
                    "title": title,
                    "description": description,
                    "color": 3447003 if is_test else 16711680,
                    "fields": [
                        {
                            "name": "Aktuální HP",
                            "value": str(hp_value),
                            "inline": True
                        },
                        {
                            "name": "Čas",
                            "value": timestamp,
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": "HP Monitor Overlay"
                    }
                }]
            }
            
            if self.discord_user_id:
                user_id = self.discord_user_id.strip()
                user_id = user_id.replace('<@', '').replace('>', '').replace('!', '')
                
                if user_id.isdigit():
                    payload["content"] = f"<@{user_id}>"
            
            response = requests.post(
                self.discord_webhook,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            return response.status_code == 204
                
        except Exception as e:
            print(f"Chyba: {e}")
            return False
    
    def test_webhook(self):
        webhook_url = self.webhook_entry.get()
        if not webhook_url:
            messagebox.showerror("Chyba", "Nejprve zadej Discord webhook URL!")
            return
        
        self.discord_webhook = webhook_url
        self.discord_user_id = self.user_id_entry.get()
        self.status_label.config(text="Odesílám test zprávu...", fg="#ffa500")
        
        def test_thread():
            success = self.send_discord_notification(100, is_test=True)
            if success:
                self.root.after(0, lambda: self.status_label.config(text="✓ Webhook funguje!", fg="#00ff88"))
                self.root.after(0, lambda: messagebox.showinfo("Úspěch", "Webhook funguje!"))
            else:
                self.root.after(0, lambda: self.status_label.config(text="✗ Webhook selhal!", fg="#ff4444"))
                self.root.after(0, lambda: messagebox.showerror("Chyba", "Webhook nefunguje!"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def toggle_compact_mode(self):
        self.compact_mode = not self.compact_mode
        
        if self.compact_mode:
            # Přepnout do compact módu - jen ikonka
            if self.expanded_mode:
                self.expanded_mode = False
                self.expand_btn.config(text="▼")
                self.hide_expanded_features()
            
            # Skryt všechno a zobrazit jen compact frame
            self.title_bar.pack_forget()
            self.content_frame.pack_forget()
            self.root.geometry("80x80")
            self.compact_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        else:
            # Přepnout zpět do full módu - musíme zachovat správné pořadí
            self.compact_frame.pack_forget()
            
            # Obnovit ve správném pořadí: title_bar nahoře, pak content
            self.title_bar.pack(fill=tk.X, side=tk.TOP)
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            
            if self.expanded_mode:
                self.root.geometry("400x750")
            else:
                self.root.geometry("400x550")
    
    def update_hp_display(self, hp_value):
        self.hp_label.config(text=str(hp_value))
    
    def set_hp_color(self, color):
        self.hp_label.config(fg=color)
    
    def save_config(self):
        config = {
            "discord_webhook": self.webhook_entry.get(),
            "discord_user_id": self.user_id_entry.get(),
            "hp_position": self.hp_position
        }
        
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Úspěch", "Konfigurace uložena!")
        except Exception as e:
            messagebox.showerror("Chyba", f"Nelze uložit: {e}")
    
    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                self.discord_webhook = config.get("discord_webhook", "")
                self.discord_user_id = config.get("discord_user_id", "")
                hp_pos = config.get("hp_position")
                if hp_pos and len(hp_pos) == 4:
                    self.hp_position = tuple(hp_pos)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Chyba: {e}")
    
    def run(self):
        self.root.mainloop()
    
    def check_for_updates(self):
        """Zkontroluje verzi a stav aplikace (EXE verze - GitHub Releases)"""
        try:
            # Kontrola zda není aplikace zrušena
            try:
                deprecated_response = requests.get(DEPRECATED_URL, timeout=5)
                if deprecated_response.status_code == 200:
                    message = deprecated_response.text.strip()
                    self.root.withdraw()
                    messagebox.showerror(
                        "Aplikace ukončena",
                        message if message else "Tato aplikace byla ukončena a nelze ji nadále používat."
                    )
                    self.root.destroy()
                    sys.exit(0)
            except requests.exceptions.RequestException:
                pass  # deprecated.txt neexistuje, pokračuj normálně
            
            # Kontrola nové verze z GitHub Releases
            response = requests.get(UPDATE_URL, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get('tag_name', '').replace('v', '')
                
                # Porovnání verzí (semantic versioning)
                def parse_version(v):
                    try:
                        return tuple(map(int, v.split('.')))
                    except:
                        return (0, 0, 0)
                
                if latest_version and parse_version(latest_version) > parse_version(VERSION):
                    # Najít HPMonitor.exe asset
                    download_url = None
                    for asset in release_data.get('assets', []):
                        if asset['name'] == 'HPMonitor.exe':
                            download_url = asset['browser_download_url']
                            break
                    
                    if download_url:
                        result = messagebox.askyesno(
                            "Nová verze dostupná",
                            f"Aktuální verze: {VERSION}\nNová verze: {latest_version}\n\nChceš stáhnout aktualizaci?"
                        )
                        
                        if result:
                            self.download_exe_update(download_url)
        except Exception as e:
            print(f"Kontrola aktualizací selhala: {e}")
    
    def download_exe_update(self, download_url):
        """Stáhne nový EXE pomocí updateru"""
        try:
            # Zkontrolovat jestli existuje updater
            if getattr(sys, 'frozen', False):
                # Běží jako EXE
                exe_path = sys.executable
                updater_path = os.path.join(os.path.dirname(exe_path), 'updater.exe')
                
                if not os.path.exists(updater_path):
                    messagebox.showerror("Chyba", "Updater nebyl nalezen!")
                    return
                
                # Spustit updater v novém terminálu
                import subprocess
                CREATE_NEW_CONSOLE = 0x00000010
                subprocess.Popen([updater_path, download_url, exe_path], 
                               creationflags=CREATE_NEW_CONSOLE)
                self.root.destroy()
                sys.exit(0)
            else:
                # Běží jako Python script - použít starou metodu
                self.download_update()
                
        except Exception as e:
            messagebox.showerror("Chyba", f"Aktualizace selhala: {e}")
    
    def download_update(self):
        """Fallback pro Python verzi"""
        try:
            files_to_update = [
                "hp_monitor.py",
                "requirements.txt",
                "README.md",
                "version.txt"
            ]
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            for filename in files_to_update:
                url = UPDATE_URL + filename
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    filepath = os.path.join(script_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
            
            messagebox.showinfo(
                "Aktualizace hotova",
                "Aplikace byla aktualizována. Restartuje se..."
            )
            
            # Restart aplikace
            python = sys.executable
            if python.endswith('python.exe'):
                python = python.replace('python.exe', 'pythonw.exe')
            
            script_path = os.path.abspath(__file__)
            subprocess.Popen([python, script_path])
            sys.exit(0)
            
        except Exception as e:
            messagebox.showerror("Chyba", f"Aktualizace selhala: {e}")

if __name__ == "__main__":
    app = HPMonitorOverlay()
    app.run()
