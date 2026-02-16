"""
Browser Utility
Handles opening URLs with specific browser profiles to avoid Profile Picker.
"""
import shutil
import subprocess
import webbrowser
from pathlib import Path

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
]

def get_chrome_path():
    """Find local Chrome executable."""
    for path in CHROME_PATHS:
        if Path(path).exists():
            return path
    return None

import pyautogui
import time

def open_url(url: str, profile: str = None):
    """
    Open a URL in Chrome.
    If profile is None, tries to handle Profile Picker by pressing Enter.
    """
    chrome_path = get_chrome_path()
    
    if chrome_path:
        try:
            # 1. Open Chrome (shows Picker if not running)
            # We assume user wants the primary profile (first one)
            subprocess.Popen([chrome_path])
            
            # Wait for Profile Picker
            time.sleep(2.5)
            
            # Press Enter to select the focused profile (usually the first/last used)
            pyautogui.press("enter")
            time.sleep(1.0)
            
            # 2. Open URL in the now-active browser
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"Failed to launch Chrome: {e}")
    
    # Fallback
    webbrowser.open(url)
    return True
