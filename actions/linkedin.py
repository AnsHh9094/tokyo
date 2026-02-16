"""
LinkedIn Automation Action
Generates content using LLM, opens LinkedIn post modal, and pastes content.
"""
import sys
import pyperclip
import webbrowser
import os
import time
from pathlib import Path
import pyautogui
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.llm import generate_text
from core.tts import edge_speak
from actions.image_generation import generate_image

LINKEDIN_URL = "https://www.linkedin.com/feed/?shareActive=true"


def create_linkedin_post(parameters: dict, response: str = None, player=None, session_memory=None):
    """
    Drafts a LinkedIn post, opens the post modal, and pastes content.
    The shareActive=true modal auto-focuses the text area — no clicking needed.
    """
    topic = parameters.get("topic")
    content = parameters.get("content")

    if not topic and not content and session_memory:
        topic = session_memory.get_last_user_text()

    if not topic and not content:
        edge_speak("Sir, what should the post be about?", player)
        return

    # 1. Notify
    if content:
        msg = "Preparing to post on LinkedIn..."
    else:
        msg = f"Drafting your LinkedIn post about {topic}..."
    if player:
        player.write_log(f"📝 {msg}")
    edge_speak(msg, player)

    # 2. Generate Content
    post_content = content
    if not post_content:
        system_prompt = (
            "You are a LinkedIn influencer and thought leader. "
            "Write a professional, engaging, and viral LinkedIn post. "
            "Use short paragraphs, emojis, and hashtags. "
            "Do not include placeholders like '[Your Name]'. "
            "The post should be ready to copy-paste."
        )
        post_content = generate_text(topic, system_prompt)

    if not post_content:
        edge_speak("Sir, I failed to generate the post content.", player)
        return

    # 3. Copy to clipboard
    pyperclip.copy(post_content)
    if player:
        player.write_log("📋 Post copied to clipboard.")

    # 4. FULLY HIDE Jarvis window using Windows API (iconify may not be enough)
    if player:
        player.write_log("🔽 Hiding Jarvis window...")
    try:
        if player and hasattr(player, 'root'):
            player.root.withdraw()  # Completely hide (not just minimize)
            time.sleep(0.5)
    except Exception:
        pass

    # 5. Open LinkedIn — browser gets full focus since Jarvis is hidden
    webbrowser.open(LINKEDIN_URL)
    if player:
        player.write_log("⏳ Waiting 20s for LinkedIn modal to load...")

    # 6. Wait for LinkedIn to fully load (it's heavy)
    time.sleep(20)

    # 7. Paste — Click to ensure focus, then paste
    try:
        # Re-copy to clipboard (safety)
        pyperclip.copy(post_content)
        time.sleep(0.5)

        # Click at 30% height (safe center area for the modal text box)
        screen_w, screen_h = pyautogui.size()
        click_x = int(screen_w * 0.5)
        click_y = int(screen_h * 0.30)
        
        if player:
            player.write_log(f"🖱️ Clicking at ({click_x}, {click_y}) to focus...")
            
        pyautogui.click(click_x, click_y)
        time.sleep(0.8)

        # Also press Tab once just in case
        pyautogui.press('tab')
        time.sleep(0.5)

        # Paste
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(3.0)

        if player:
            player.write_log("✅ Content pasted into LinkedIn!")
            player.write_log("👆 Please verify and click Post manually.")

    except Exception as e:
        if player:
            player.write_log(f"⚠️ Paste error: {e}")
            player.write_log("📋 Content is on clipboard — Ctrl+V manually.")

    # 8. Restore Jarvis window after a delay
    time.sleep(3.0)
    try:
        if player and hasattr(player, 'root'):
            player.root.deiconify()  # Show window again
    except Exception:
        pass

    edge_speak("Content pasted into LinkedIn. Please verify and click Post.", player)
