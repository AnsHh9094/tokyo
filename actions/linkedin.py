"""
LinkedIn Automation Action
Generates content, opens LinkedIn post modal, and pastes content.
Uses LinkedIn's ?shareActive=true which auto-opens and auto-focuses the modal.
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
    LinkedIn's shareActive=true auto-opens the modal with text area focused.
    """
    topic = parameters.get("topic")
    content = parameters.get("content")

    if not topic and not content and session_memory:
        topic = session_memory.get_last_user_text()

    if not topic and not content:
        edge_speak("Sir, what should the post be about?", player)
        return

    # ── Step 1: Notify ──────────────────────────────────────
    if content:
        msg = "Preparing to post on LinkedIn..."
    else:
        msg = f"Drafting your LinkedIn post about {topic}..."
    if player:
        player.write_log(f"📝 {msg}")
    edge_speak(msg, player)

    # ── Step 2: Generate Content ────────────────────────────
    post_content = content
    if not post_content:
        system_prompt = (
            "You are a LinkedIn influencer and thought leader. "
            "Write a professional, engaging, and viral LinkedIn post. "
            "Use short paragraphs, emojis, and hashtags. "
            "Keep it under 200 words. "
            "Do not include placeholders like '[Your Name]'. "
            "The post should be ready to copy-paste."
        )
        post_content = generate_text(topic, system_prompt)

    if not post_content:
        edge_speak("Sir, I failed to generate the post content.", player)
        return

    # ── Step 3: Generate Image if topic suggests it ─────────
    image_path = None
    needs_image = any(
        w in (topic or "").lower() 
        for w in ["image", "picture", "photo", "graphic", "visual", "banner"]
    )
    if needs_image and topic:
        if player:
            player.write_log("🎨 Generating image for the post...")
        image_path = generate_image(topic)
        if image_path and player:
            player.write_log(f"✅ Image ready: {Path(image_path).name}")

    # ── Step 4: Copy content to clipboard ───────────────────
    pyperclip.copy(post_content)
    if player:
        player.write_log(f"📋 Post copied ({len(post_content)} chars)")

    # ── Step 5: Hide Jarvis window ──────────────────────────
    try:
        if player and hasattr(player, 'root'):
            player.root.withdraw()
            time.sleep(0.3)
    except Exception:
        pass

    # ── Step 6: Open LinkedIn with auto-focused post modal ──
    # The ?shareActive=true parameter opens the post modal AND
    # auto-focuses the text area — no clicking needed.
    webbrowser.open(LINKEDIN_URL)
    if player:
        player.write_log("⏳ Opening LinkedIn...")

    # Wait for page + modal to fully load
    time.sleep(12)

    # ── Step 7: Paste content ───────────────────────────────
    # The modal text area is already focused by LinkedIn.
    # Just re-copy (safety) and paste.
    try:
        pyperclip.copy(post_content)
        time.sleep(0.5)
        
        # Paste with Ctrl+V — text area is already focused
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(2.0)

        if player:
            player.write_log("✅ Content pasted into LinkedIn!")

        # If we have an image, open it so user can drag it in
        if image_path and os.path.exists(image_path):
            if player:
                player.write_log(f"📸 Image saved at: {image_path}")
                player.write_log("💡 Drag the image into the post, or use the media button.")
            # Open the image file location
            try:
                subprocess.run(['explorer', '/select,', image_path], shell=True)
            except:
                pass

        edge_speak("Content is pasted. Please review and click Post when ready.", player)

    except Exception as e:
        if player:
            player.write_log(f"⚠️ Paste error: {e}")
            player.write_log("📋 Content is on clipboard — Ctrl+V manually.")
        edge_speak("Sir, content is on your clipboard. Please paste manually.", player)

    # ── Step 8: Restore Jarvis window after delay ───────────
    time.sleep(5.0)
    try:
        if player and hasattr(player, 'root'):
            player.root.deiconify()
    except Exception:
        pass
