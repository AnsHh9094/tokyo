"""Quick test: Does the click land on the right spot?"""
import pyautogui
import ctypes
from ctypes import wintypes
import os, time

pyautogui.FAILSAFE = False

def find_spotify():
    found = None
    def cb(hwnd, lp):
        nonlocal found
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        if ctypes.windll.user32.IsWindowVisible(hwnd) and "Spotify" in buff.value:
            found = hwnd
            return False
        return True
    proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    ctypes.windll.user32.EnumWindows(proc(cb), 0)
    return found

# 1. Search
query = "sicko mode"
print(f"Searching '{query}'...")
os.startfile(f"spotify:search:{query}")
print("Waiting 5s...")
time.sleep(5.0)

# 2. Focus
hwnd = find_spotify()
if not hwnd:
    print("❌ Spotify window not found!")
    exit(1)

# Alt trick + focus
pyautogui.press('alt')
time.sleep(0.1)
pyautogui.press('alt')
ctypes.windll.user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# 3. Get window rect
rect = wintypes.RECT()
ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
win_x, win_y = rect.left, rect.top
win_w = rect.right - rect.left
win_h = rect.bottom - rect.top
print(f"Window: x={win_x}, y={win_y}, w={win_w}, h={win_h}")

# 4. Calculate target (Top Result card area)
click_x = win_x + int(win_w * 0.30)
click_y = win_y + int(win_h * 0.42)
print(f"Clicking at: ({click_x}, {click_y})")

# 5. Move and double-click
pyautogui.moveTo(click_x, click_y, duration=0.3)
time.sleep(0.2)
pyautogui.doubleClick(click_x, click_y)

print("✅ Double-clicked! Check if song is playing.")
