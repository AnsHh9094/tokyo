import pyautogui
import time
import sys
import os

# ... (Keep imports)
import ctypes
pyautogui.FAILSAFE = False # Disable fail-safe to prevent crash

def get_spotify_title():
    # ... (Keep existing function)
    pass # (Placeholder for tool)

def focus_spotify_window():
    """Focus Spotify window (Enhanced)"""
    found_hwnd = None
    def enum_windows_callback(hwnd, lParam):
        nonlocal found_hwnd
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        # Check if visible
        if ctypes.windll.user32.IsWindowVisible(hwnd):
             if "Spotify" in title or "- " in title: 
                 if "Spotify" in title:
                     found_hwnd = hwnd
                     return False
        return True

    try:
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        ctypes.windll.user32.EnumWindows(enum_proc(enum_windows_callback), 0)
        
        if found_hwnd:
            if ctypes.windll.user32.IsIconic(found_hwnd):
                ctypes.windll.user32.ShowWindow(found_hwnd, 9) # SW_RESTORE
            
            # Trick to force focus: Press Alt key
            pyautogui.press('alt') 
            time.sleep(0.1)
            pyautogui.press('alt')
            
            ctypes.windll.user32.SetForegroundWindow(found_hwnd)
            time.sleep(0.2)
            return True
        return False
    except:
        return False

# ... (rest of script)


def get_spotify_title():
    """Get the title of the visible Spotify window."""
    found_title = ""
    def enum_windows_callback(hwnd, lParam):
        nonlocal found_title
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        if ctypes.windll.user32.IsWindowVisible(hwnd):
             if "Spotify" in title or "- " in title: 
                 found_title = title
                 return False
        return True

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    ctypes.windll.user32.EnumWindows(enum_proc(enum_windows_callback), 0)
    return found_title

def test_sequence(seq_num):
    print(f"Testing Sequence #{seq_num}...")
    
    # 1. Open
    query = "sicko mode"
    print(f"   Searching for '{query}'...")
    os.startfile(f"spotify:search:{query}")
    
    print("   Waiting 5 seconds for load...")
    time.sleep(5.0)
    
    # Ensure Focus!
    focus_spotify_window()
    time.sleep(0.5)

    title_before = get_spotify_title()
    print(f"   [Before] Window Title: '{title_before}'")
    
    # 2. Execute Sequence
    if seq_num == 1:
        print("   [Seq 1] Just ENTER")
        pyautogui.press("enter")

    elif seq_num == 2:
        print("   [Seq 2] Tab -> Enter")
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("enter")

    elif seq_num == 3:
        print("   [Seq 3] Tab -> Tab -> Enter")
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("enter")

    elif seq_num == 4:
        print("   [Seq 4] Tab -> Tab -> Tab -> Enter")
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("enter")

    elif seq_num == 5:
        print("   [Seq 5] SPACEBAR")
        pyautogui.press("space")

    elif seq_num == 6:
        print("   [Seq 6] Tab -> SPACEBAR")
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("space")

    elif seq_num == 7:
        print("   [Seq 7] CTRL+ENTER")
        pyautogui.hotkey("ctrl", "enter")

    # 3. Check Result
    time.sleep(2.0)
    title_after = get_spotify_title()
    print(f"   [After] Window Title: '{title_after}'")
    
    if title_before != title_after and ("-" in title_after or "Sicko" in title_after):
        print("   ✅ SUCCESS! Title changed, music likely playing.")
    elif title_after == title_before:
        print("   ❌ NO CHANGE. Music probably not playing.")
    else:
        print("   ⚠️ Unknown. Title changed but maybe not to song?")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_sequence(int(sys.argv[1]))
    else:
        print("Run with a sequence number to test:")
        print("python debug_spotify_v2.py 1  (Enter)")
        print("python debug_spotify_v2.py 2  (Tab -> Enter)")
        print("python debug_spotify_v2.py 3  (2 Tabs -> Enter)")
        print("python debug_spotify_v2.py 4  (3 Tabs -> Enter)")
        print("python debug_spotify_v2.py 5  (Spacebar)")
        print("python debug_spotify_v2.py 6  (Tab -> Spacebar)")
        print("python debug_spotify_v2.py 7  (Ctrl + Enter)")
