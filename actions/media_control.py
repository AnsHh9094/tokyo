
"""
Media Control Action
Handles media playback (play, pause, next, previous) and Spotify search found.
"""
import time
import pyautogui
import os
import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.tts import edge_speak

import urllib.parse
import ctypes
from ctypes import wintypes

# Windows API constants
SW_RESTORE = 9
SW_SHOW = 5
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _get_process_name(pid):
    """Get process executable name from PID."""
    try:
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h:
            buf = ctypes.create_unicode_buffer(260)
            size = wintypes.DWORD(260)
            if ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                ctypes.windll.kernel32.CloseHandle(h)
                return buf.value.lower()
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        pass
    return ""

def _find_spotify_hwnd():
    """Find the Spotify window handle by checking process name (not title)."""
    found_hwnd = None
    
    def enum_cb(hwnd, lParam):
        nonlocal found_hwnd
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        # Get window title length — skip windows with no title
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        # Get the process ID for this window
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = _get_process_name(pid.value)
        if "spotify.exe" in proc_name:
            found_hwnd = hwnd
            return False  # Stop enumeration
        return True
    
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    ctypes.windll.user32.EnumWindows(enum_proc(enum_cb), 0)
    return found_hwnd


def focus_spotify_window() -> bool:
    """Focus the Spotify window using process-based detection."""
    try:
        hwnd = _find_spotify_hwnd()
        if hwnd:
            # Restore if minimized
            if ctypes.windll.user32.IsIconic(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            
            # Robust Focus Trick: Press Alt to grab attention, then focus
            pyautogui.press('alt')
            time.sleep(0.1)
            pyautogui.press('alt')
            
            # Bring to front
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            return True
        return False
    except Exception as e:
        print(f"Focus Error: {e}")
        return False


def media_control(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Control global media playback.
    """
    command = (parameters or {}).get("command", "").lower()
    
    mapping = {
        "play": "playpause",
        "pause": "playpause",
        "resume": "playpause",
        "stop": "stop",
        "next": "nexttrack",
        "skip": "nexttrack",
        "previous": "prevtrack",
        "back": "prevtrack",
        "volume_up": "volumeup",
        "volume_down": "volumedown",
        "mute": "volumemute",
    }
    
    key = mapping.get(command)
    
    if not key:
        msg = f"Sir, I don't know the media command '{command}'."
        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return False

    try:
        # Focus Spotify first for playback commands
        if command in ["play", "pause", "resume", "next", "previous", "skip", "back"]:
            focused = focus_spotify_window()
            if not focused and player:
               player.write_log("⚠️ Could not focus Spotify window explicitly.")
            
        pyautogui.press(key)
        
        # Feedback logic...
        action_verb = command.capitalize()
        if command in ["play", "resume"]:
            msg = response or "Resuming playback."
        elif command == "pause":
            msg = response or "Pausing playback."
        elif command in ["next", "skip"]:
            msg = response or "Skipping to next track."
        elif command in ["previous", "back"]:
            msg = response or "Going back to previous track."
        else:
            msg = response or f"{action_verb} command sent."

        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return True

    except Exception as e:
        msg = f"Sir, media control failed: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False


# _find_spotify_hwnd is now defined above (uses process-based detection)


def spotify_play(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Search and play a song on Spotify.
    Clicks the search bar directly, types the query, then double-clicks the first result.
    Works whether Spotify is already open or not.
    """
    query = (parameters or {}).get("query", "").strip()
    
    if not query:
        msg = "Sir, what should I play?"
        edge_speak(msg, player)
        return False
        
    try:
        if player:
            player.write_log(f"Jarvis: Searching Spotify for '{query}'...")

        # 1. Make sure Spotify is open
        hwnd = _find_spotify_hwnd()
        if not hwnd:
            # Spotify not open — launch it
            os.startfile("spotify:")
            time.sleep(5.0)
            hwnd = _find_spotify_hwnd()
        
        # 2. Focus and get window position
        focus_spotify_window()
        time.sleep(0.5)
        
        hwnd = _find_spotify_hwnd()
        if not hwnd:
            if player:
                player.write_log("Jarvis: Could not find Spotify window.")
            edge_speak("Sir, I couldn't find the Spotify window.", player)
            return False
        
        # Get window rectangle
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        win_x = rect.left
        win_y = rect.top
        win_w = rect.right - rect.left
        win_h = rect.bottom - rect.top
        
        if player:
            player.write_log(f"Jarvis: Spotify window at ({win_x},{win_y}) size {win_w}x{win_h}")

        # 3. Click the search bar at top center
        # From the screenshot: search bar is at ~50% width, ~2-3% from top (the very top bar)
        search_x = win_x + int(win_w * 0.45)
        search_y = win_y + int(win_h * 0.035)
        
        if player:
            player.write_log(f"Jarvis: Clicking search bar at ({search_x}, {search_y})...")
        
        pyautogui.click(search_x, search_y)
        time.sleep(0.8)
        
        # 4. Clear existing text and type the query
        pyautogui.hotkey('ctrl', 'a')  # Select all in search bar
        time.sleep(0.2)
        pyautogui.press('delete')      # Clear
        time.sleep(0.3)
        
        # Type the search query using clipboard (supports non-ASCII like Hindi)
        import pyperclip
        pyperclip.copy(query)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(3.0)  # Wait for search results to load
        
        if player:
            player.write_log("Jarvis: Search results loaded, playing first song...")

        # 5. Double-click the first song in the Songs list
        # From screenshot: first song row is at ~27% from top, 55% from left
        # (35% was hitting the 2nd song)
        song_x = win_x + int(win_w * 0.55)
        song_y = win_y + int(win_h * 0.27)
        
        if player:
            player.write_log(f"Jarvis: Double-clicking first song at ({song_x}, {song_y})...")
        
        pyautogui.doubleClick(song_x, song_y)
        time.sleep(1.5)
        
        msg = response or f"Playing {query} on Spotify."
        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return True

    except Exception as e:
        msg = f"Sir, I failed to play on Spotify: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False


def youtube_play(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Search and play a video on YouTube by opening the search results page.
    The first result auto-plays in the browser.
    """
    query = (parameters or {}).get("query", "").strip()
    
    if not query:
        msg = "Sir, what should I search on YouTube?"
        edge_speak(msg, player)
        return False
    
    try:
        if player:
            player.write_log(f"Jarvis: Searching YouTube for '{query}'...")

        # Open YouTube search results directly
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        import webbrowser
        webbrowser.open(url)
        
        # Wait for page to load
        time.sleep(4.0)
        
        # Click on the first video result to play it
        # YouTube layout: first video thumbnail is roughly at 40% from left, 35% from top
        try:
            pyautogui.click(x=600, y=350)  # Approximate first result position
            time.sleep(0.5)
        except Exception:
            pass
        
        msg = response or f"Playing {query} on YouTube."
        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return True

    except Exception as e:
        msg = f"Sir, YouTube search failed: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False
