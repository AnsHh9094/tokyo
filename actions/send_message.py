"""
Send Message Action — WhatsApp, Telegram, etc.
Uses pyautogui for Windows desktop automation.
Multi-step: asks for missing parameters using session memory.
Based on Mark-X.1 by FatihMakes.
"""
import time
import pyautogui
import pyperclip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.tts import edge_speak
from core.browser import open_url
import webbrowser

REQUIRED_PARAMS = ["receiver", "message_text", "platform"]


def send_message(parameters: dict, response: str = None, player=None, session_memory=None) -> bool:
    """
    Send a message via Windows app (WhatsApp, Telegram, etc.)

    Multi-step support: asks for missing parameters using temporary memory.

    Expected parameters:
        - receiver (str): Contact name
        - message_text (str): Message content
        - platform (str): "whatsapp", "telegram", etc.
    """

    if session_memory is None:
        msg = "Session memory missing, cannot proceed."
        if player:
            player.write_log(msg)
        edge_speak(msg, player)
        return False

    # Merge any new parameters
    if parameters:
        session_memory.update_parameters(parameters)

    # Check for missing parameters and ask
    for param in REQUIRED_PARAMS:
        value = session_memory.get_parameter(param)
        if not value:
            session_memory.set_current_question(param)

            if param == "receiver":
                question = "Sir, who should I send the message to?"
            elif param == "message_text":
                question = "Sir, what should I say?"
            elif param == "platform":
                question = "Sir, which platform? WhatsApp or Telegram?"
            else:
                question = f"Sir, please provide {param}."

            if player:
                player.write_log(f"AI: {question}")
            edge_speak(question, player)
            return False  # Wait for user's answer

    # All parameters collected — send the message
    receiver = session_memory.get_parameter("receiver").strip()
    platform = session_memory.get_parameter("platform").strip() or "WhatsApp"
    message_text = session_memory.get_parameter("message_text").strip()

    # ══════════════════════════════════════════════════════
    #  INSTAGRAM SUPPORT (Web)
    # ══════════════════════════════════════════════════════
    if "instagram" in platform.lower():
        try:
            # Use deep link to open DM directly
            # Receiver must be the exact username
            url = f"https://ig.me/m/{receiver}"
            
            if response:
                edge_speak(response, player)
            
            open_url(url)  # Use core.browser logic to select profile
            
            # Instagram takes time to load
            time.sleep(6.0) 
            
            # Type message
            pyperclip.copy(message_text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            
            # Send
            pyautogui.press("enter")
            
            success_msg = f"Sir, message sent to {receiver} on Instagram."
            if player:
                player.write_log(f"✅ {success_msg}")
            edge_speak(success_msg, player)
            return True

        except Exception as e:
            print(f"IG Error: {e}")
            return False

    # ══════════════════════════════════════════════════════
    #  DESKTOP APPS (WhatsApp, Telegram)
    # ══════════════════════════════════════════════════════

    if response:
        if player:
            player.write_log(f"AI: {response}")
        edge_speak(response, player)

    try:
        pyautogui.PAUSE = 0.1

        # Open the platform app via Windows search
        pyautogui.press("win")
        time.sleep(0.4)
        pyautogui.write(platform, interval=0.03)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(2.5)  # Wait for app to fully open

        # Search for contact
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.5)

        # Use pyperclip for non-ASCII contact names
        pyperclip.copy(receiver)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.0)

        # Select first search result
        pyautogui.press("enter")
        time.sleep(0.8)

        # Type the message (use clipboard for Unicode support)
        pyperclip.copy(message_text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)

        # Send
        pyautogui.press("enter")
        time.sleep(0.5)

        # Clear session memory
        session_memory.clear_current_question()
        session_memory.clear_pending_intent()
        session_memory.update_parameters({})

        success_msg = f"Sir, message sent to {receiver} via {platform}."
        if player:
            player.write_log(f"✅ {success_msg}")
        edge_speak(success_msg, player)

        return True

    except Exception as e:
        msg = f"Sir, I failed to send the message. ({e})"
        if player:
            player.write_log(f"❌ {msg}")
        edge_speak(msg, player)
        return False
