"""
Open Application Action
Uses Windows search to launch applications by name.
"""
import time
import pyautogui
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.tts import edge_speak


# Common app aliases for better recognition
APP_ALIASES = {
    "whatsapp": "WhatsApp",
    "what's up": "WhatsApp",
    "what's app": "WhatsApp",
    "chrome": "Google Chrome",
    "firefox": "Firefox",
    "edge": "Microsoft Edge",
    "notepad": "Notepad",
    "calculator": "Calculator",
    "calc": "Calculator",
    "paint": "Paint",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "ppt": "Microsoft PowerPoint",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "terminal": "Terminal",
    "cmd": "Command Prompt",
    "powershell": "PowerShell",
    "spotify": "Spotify",
    "discord": "Discord",
    "telegram": "Telegram",
    "file explorer": "File Explorer",
    "explorer": "File Explorer",
    "files": "File Explorer",
    "settings": "Settings",
    "task manager": "Task Manager",
    "steam": "Steam",
    "obs": "OBS Studio",
    "vlc": "VLC",
    "photos": "Photos",
    "camera": "Camera",
    "store": "Microsoft Store",
    "outlook": "Outlook",
    "teams": "Microsoft Teams",
    "zoom": "Zoom",
    "slack": "Slack",
    "notion": "Notion",
    "figma": "Figma",
}


def open_app(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Open an application using Windows search.

    Args:
        parameters: dict with 'app_name' key
        response: AI response text to speak
        player: JarvisUI instance
        session_memory: TemporaryMemory instance
    """
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name and session_memory:
        app_name = session_memory.open_app or ""

    if not app_name:
        msg = "Sir, I couldn't determine which application to open."
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    # Check for aliases
    app_name_lower = app_name.lower()
    resolved_name = APP_ALIASES.get(app_name_lower, app_name)

    if response:
        if player:
            player.write_log(f"Jarvis: {response}")
        edge_speak(response, player)

    try:
        pyautogui.PAUSE = 0.1

        # Press Win key to open search
        pyautogui.press("win")
        time.sleep(0.4)

        # Type the app name
        pyautogui.write(resolved_name, interval=0.03)
        time.sleep(0.3)

        # Press Enter to launch
        pyautogui.press("enter")
        time.sleep(0.5)

        if session_memory:
            session_memory.set_open_app(resolved_name)

        print(f"✅ Opened: {resolved_name}")
        return True

    except Exception as e:
        msg = f"Sir, I failed to open {resolved_name}."
        if player:
            player.write_log(f"{msg} ({e})")
        edge_speak(msg, player)
        return False
