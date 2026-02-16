"""
Make Call Action — WhatsApp
Uses `whatsapp://` protocol and optimized pyautogui for speed.
"""
import time
import pyautogui
import pyperclip
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.tts import edge_speak

REQUIRED_PARAMS = ["receiver", "platform"]


def make_call(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Make a voice/video call via Windows app (WhatsApp).
    Optimized for speed using protocol handlers.
    """

    if session_memory is None:
        return False

    # Merge any new parameters
    if parameters:
        session_memory.update_parameters(parameters)

    # Check for missing parameters
    for param in REQUIRED_PARAMS:
        value = session_memory.get_parameter(param)
        if not value:
            session_memory.set_current_question(param)
            question = f"Sir, who should I call?" if param == "receiver" else f"Unknown platform."
            if player:
                player.write_log(f"AI: {question}")
            edge_speak(question, player)
            return False

    receiver = session_memory.get_parameter("receiver").strip()
    platform = session_memory.get_parameter("platform").strip() or "WhatsApp"

    if "whatsapp" not in platform.lower():
        edge_speak("Sir, I only support WhatsApp calls right now.", player)
        return False

    if response:
        edge_speak(response, player)

    try:
        pyautogui.PAUSE = 0.05  # Faster typing/clicks

        # 1. Open WhatsApp fast via Protocol
        # This brings window to front immediately if open
        os.system("start whatsapp:") 
        time.sleep(1.2) # Fast wait

        # 2. Search for contact
        # Focus search bar
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)

        # Type/Paste name
        pyperclip.copy(receiver)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.7) # Wait for search results

        # 3. Select Contact
        pyautogui.press("down") # Select first result safely
        pyautogui.press("enter")
        time.sleep(0.5)

        # 4. Call
        # WhatsApp Desktop Shortcuts:
        # Voice Call: Ctrl + Shift + C
        print(f"📞 Calling {receiver}...")
        pyautogui.hotkey("ctrl", "shift", "c")
        
        # Cleanup
        session_memory.clear_current_question()
        session_memory.clear_pending_intent()
        session_memory.update_parameters({})

        if player:
            player.write_log(f"✅ Calling {receiver}...")
        
        return True

    except Exception as e:
        msg = f"Sir, I failed to place the call. ({e})"
        if player:
            player.write_log(f"❌ {msg}")
        edge_speak(msg, player)
        return False
