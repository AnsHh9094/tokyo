"""
System Control Actions
Handles system info, file operations, clipboard, screenshot, volume,
timer, notes, calculator, and shutdown/restart/lock.
"""
import os
import sys
import time
import math
import shutil
import ctypes
import subprocess
import threading
import pyperclip
import psutil
import pyautogui
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.tts import edge_speak
from memory.memory_manager import add_note, get_notes


# ═══════════════════════════════════════════════════════════════
#  SYSTEM INFORMATION
# ═══════════════════════════════════════════════════════════════

def system_info(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Get system information: CPU, RAM, disk, battery."""
    info_type = (parameters or {}).get("info_type", "all").lower()

    info_parts = []

    if info_type in ("cpu", "all"):
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{cpu_freq.current:.0f}MHz" if cpu_freq else "unknown"
        info_parts.append(f"CPU: {cpu_percent}% usage, {cpu_count} cores at {freq_str}")

    if info_type in ("ram", "memory", "all"):
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        info_parts.append(f"RAM: {used_gb:.1f}/{total_gb:.1f} GB ({mem.percent}%)")

    if info_type in ("disk", "storage", "all"):
        partitions = psutil.disk_partitions()
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                used_gb = usage.used / (1024 ** 3)
                total_gb = usage.total / (1024 ** 3)
                info_parts.append(f"Disk {p.device}: {used_gb:.1f}/{total_gb:.1f} GB ({usage.percent}%)")
            except PermissionError:
                continue

    if info_type in ("battery", "all"):
        battery = psutil.sensors_battery()
        if battery:
            plugged = "charging" if battery.power_plugged else "on battery"
            info_parts.append(f"Battery: {battery.percent}% ({plugged})")
        else:
            info_parts.append("Battery: Not available (desktop PC)")

    result = " | ".join(info_parts)
    msg = response or f"Sir, {result}"

    if player:
        player.write_log(f"Jarvis: {msg}")
        for part in info_parts:
            player.write_log(f"  📊 {part}")
    edge_speak(msg, player)
    return True


# ═══════════════════════════════════════════════════════════════
#  FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════

def file_operation(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Handle file/folder create, delete, move, find, list operations."""
    operation = (parameters or {}).get("operation", "").lower()
    path_str = (parameters or {}).get("path", "").strip()
    destination = (parameters or {}).get("destination", "").strip()

    if not path_str:
        msg = "Sir, I need a file or folder path to work with."
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    # Expand ~ and environment variables
    path = Path(os.path.expandvars(os.path.expanduser(path_str)))

    # Safety check
    dangerous_paths = [Path("C:/Windows"), Path("C:/Program Files"), Path("C:/")]
    for dp in dangerous_paths:
        try:
            if path.resolve().is_relative_to(dp.resolve()) and operation in ("delete", "move"):
                msg = f"Sir, I cannot {operation} files in {dp}. That's a protected system directory."
                if player:
                    player.write_log(msg)
                edge_speak(msg, player)
                return False
        except Exception:
            pass

    try:
        if operation == "create":
            if path.suffix:  # Has extension = file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
                msg = response or f"Sir, I've created the file: {path.name}"
            else:  # Directory
                path.mkdir(parents=True, exist_ok=True)
                msg = response or f"Sir, I've created the folder: {path.name}"

        elif operation == "delete":
            if path.is_file():
                path.unlink()
                msg = response or f"Sir, I've deleted the file: {path.name}"
            elif path.is_dir():
                shutil.rmtree(path)
                msg = response or f"Sir, I've deleted the folder: {path.name}"
            else:
                msg = f"Sir, I couldn't find: {path}"

        elif operation == "move":
            if not destination:
                msg = "Sir, I need a destination path for the move."
            else:
                dest = Path(os.path.expandvars(os.path.expanduser(destination)))
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(dest))
                msg = response or f"Sir, I've moved {path.name} to {dest}"

        elif operation == "find":
            # Search in common directories
            search_dirs = [
                Path.home() / "Desktop",
                Path.home() / "Documents",
                Path.home() / "Downloads",
            ]
            found = []
            search_name = path_str.lower()
            for search_dir in search_dirs:
                if search_dir.exists():
                    for item in search_dir.rglob("*"):
                        if search_name in item.name.lower():
                            found.append(str(item))
                            if len(found) >= 10:
                                break

            if found:
                msg = response or f"Sir, I found {len(found)} matches."
                if player:
                    for f in found[:5]:
                        player.write_log(f"  📁 {f}")
            else:
                msg = f"Sir, I couldn't find any files matching '{path_str}'."

        elif operation == "list":
            if path.is_dir():
                items = list(path.iterdir())[:20]
                msg = response or f"Sir, {path.name} contains {len(list(path.iterdir()))} items."
                if player:
                    for item in items:
                        icon = "📁" if item.is_dir() else "📄"
                        player.write_log(f"  {icon} {item.name}")
            else:
                msg = f"Sir, {path} is not a directory."
        else:
            msg = f"Sir, I don't know the operation '{operation}'."

        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return True

    except PermissionError:
        msg = f"Sir, I don't have permission to {operation} at that location."
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False
    except Exception as e:
        msg = f"Sir, file operation failed: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False


# ═══════════════════════════════════════════════════════════════
#  CLIPBOARD
# ═══════════════════════════════════════════════════════════════

def clipboard_action(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Read or write clipboard content."""
    action = (parameters or {}).get("action", "read").lower()
    content = (parameters or {}).get("content", "")

    try:
        if action == "read":
            text = pyperclip.paste()
            if text:
                msg = response or f"Sir, your clipboard contains: {text[:200]}"
                if player:
                    player.write_log(f"📋 Clipboard: {text[:500]}")
            else:
                msg = "Sir, your clipboard is empty."
            if player:
                player.write_log(f"Jarvis: {msg}")
            edge_speak(msg, player)

        elif action == "write":
            if content:
                pyperclip.copy(content)
                msg = response or f"Sir, I've copied that to your clipboard."
                if player:
                    player.write_log(f"Jarvis: {msg}")
                edge_speak(msg, player)
            else:
                msg = "Sir, what would you like me to copy?"
                if player:
                    player.write_log(msg)
                edge_speak(msg, player)

        return True

    except Exception as e:
        msg = f"Sir, clipboard error: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False


# ═══════════════════════════════════════════════════════════════
#  SCREENSHOT
# ═══════════════════════════════════════════════════════════════

def take_screenshot(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Capture a screenshot and save it."""
    try:
        screenshots_dir = Path.home() / "Pictures" / "Jarvis_Screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = screenshots_dir / f"screenshot_{timestamp}.png"

        screenshot = pyautogui.screenshot()
        screenshot.save(str(filename))

        msg = response or f"Sir, screenshot saved to {filename.name}"
        if player:
            player.write_log(f"Jarvis: {msg}")
            player.write_log(f"  📸 {filename}")
        edge_speak(msg, player)
        return True

    except Exception as e:
        msg = f"Sir, couldn't take screenshot: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False


# ═══════════════════════════════════════════════════════════════
#  VOLUME CONTROL
# ═══════════════════════════════════════════════════════════════

def volume_control(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Control system volume using keyboard shortcuts."""
    action = (parameters or {}).get("action", "").lower()

    try:
        if action == "mute":
            pyautogui.press("volumemute")
            msg = response or "Sir, I've muted the volume."
        elif action == "unmute":
            pyautogui.press("volumemute")
            msg = response or "Sir, I've unmuted the volume."
        elif action == "up":
            for _ in range(5):
                pyautogui.press("volumeup")
            msg = response or "Sir, volume increased."
        elif action == "down":
            for _ in range(5):
                pyautogui.press("volumedown")
            msg = response or "Sir, volume decreased."
        elif action == "set":
            level = int((parameters or {}).get("level", 50))
            # Mute first, then increase to target
            pyautogui.press("volumemute")
            time.sleep(0.1)
            pyautogui.press("volumemute")
            # Each press is ~2% change, so level/2 presses
            steps = level // 2
            for _ in range(steps):
                pyautogui.press("volumeup")
            msg = response or f"Sir, volume set to approximately {level}%."
        else:
            msg = f"Sir, I don't understand the volume action '{action}'."

        if player:
            player.write_log(f"Jarvis: {msg}")
        edge_speak(msg, player)
        return True

    except Exception as e:
        msg = f"Sir, volume control error: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False


# ═══════════════════════════════════════════════════════════════
#  TIMER
# ═══════════════════════════════════════════════════════════════

def set_timer(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Set a countdown timer."""
    duration = int((parameters or {}).get("duration_seconds", 0))
    label = (parameters or {}).get("label", "Timer")

    if duration <= 0:
        msg = "Sir, please specify a valid timer duration."
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    msg = response or f"Sir, timer set for {duration} seconds."
    if player:
        player.write_log(f"Jarvis: {msg}")
    edge_speak(msg, player)

    def _timer_thread():
        time.sleep(duration)
        alert = f"Sir, your {label} timer is up! {duration} seconds have elapsed."
        if player:
            player.write_log(f"⏰ {alert}")
        edge_speak(alert, player)

    threading.Thread(target=_timer_thread, daemon=True).start()
    return True


# ═══════════════════════════════════════════════════════════════
#  CALCULATOR
# ═══════════════════════════════════════════════════════════════

def calculate(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Evaluate math expressions safely."""
    expression = (parameters or {}).get("expression", "").strip()

    if not expression:
        msg = "Sir, what would you like me to calculate?"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    # Safe math evaluation
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow, "int": int, "float": float,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "pi": math.pi, "e": math.e,
        "log": math.log, "log10": math.log10, "ceil": math.ceil,
        "floor": math.floor,
    }

    try:
        # Basic safety: only allow math characters
        safe_chars = set("0123456789+-*/().,%^ ")
        expr_check = expression.replace(" ", "")
        for name in allowed_names:
            expr_check = expr_check.replace(name, "")

        result = eval(expression, {"__builtins__": {}}, allowed_names)
        msg = response or f"Sir, the result is {result}"
        if player:
            player.write_log(f"Jarvis: {expression} = {result}")
        edge_speak(msg, player)
        return True

    except Exception as e:
        msg = f"Sir, I couldn't calculate that: {e}"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False


# ═══════════════════════════════════════════════════════════════
#  NOTES
# ═══════════════════════════════════════════════════════════════

def take_note_action(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Save a note to persistent memory."""
    title = (parameters or {}).get("title", "Untitled")
    content = (parameters or {}).get("content", "")

    if not content:
        msg = "Sir, what should the note say?"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    add_note(title, content)
    msg = response or f"Sir, I've saved your note: '{title}'."
    if player:
        player.write_log(f"Jarvis: {msg}")
    edge_speak(msg, player)
    return True


def read_notes_action(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Read saved notes."""
    notes = get_notes()

    if not notes:
        msg = "Sir, you don't have any saved notes."
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return True

    msg = response or f"Sir, you have {len(notes)} notes."
    if player:
        player.write_log(f"Jarvis: {msg}")
        for i, note in enumerate(notes, 1):
            player.write_log(f"  📝 [{i}] {note['title']}: {note['content'][:100]}")

    edge_speak(msg, player)
    return True


# ═══════════════════════════════════════════════════════════════
#  SHUTDOWN / RESTART / SLEEP / LOCK
# ═══════════════════════════════════════════════════════════════

def shutdown_action(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """Shutdown, restart, sleep, or lock the PC."""
    action = (parameters or {}).get("action", "").lower()
    delay = int((parameters or {}).get("delay_seconds", 0))

    if action not in ("shutdown", "restart", "sleep", "lock"):
        msg = "Sir, would you like me to shutdown, restart, sleep, or lock?"
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    # Warn user
    if delay > 0:
        warning = response or f"Sir, I'll {action} the PC in {delay} seconds."
    else:
        warning = response or f"Sir, initiating {action} now."

    if player:
        player.write_log(f"⚠️ {warning}")
    edge_speak(warning, player, blocking=True)

    def _execute():
        if delay > 0:
            time.sleep(delay)

        if action == "shutdown":
            os.system("shutdown /s /t 5")
        elif action == "restart":
            os.system("shutdown /r /t 5")
        elif action == "sleep":
            ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
        elif action == "lock":
            ctypes.windll.user32.LockWorkStation()

    threading.Thread(target=_execute, daemon=True).start()
    return True
