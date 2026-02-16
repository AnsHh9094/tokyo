import sys
import time
from core.tts import edge_speak
from actions.linkedin import create_linkedin_post

def test_tts_filtering():
    print("Testing TTS Emoji Filtering...")
    text_with_emojis = "Hello sir! This is a test message with emojis 😀 🚀. You should not hear the emoji names."
    print(f"Original Text: {text_with_emojis}")
    print("Speaking...")
    edge_speak(text_with_emojis, blocking=True)
    print("Done speaking.")

def test_linkedin_automation():
    print("\nTesting LinkedIn Automation...")
    print("⚠️ WARNING: This will open LinkedIn in your default browser.")
    print("⚠️ When the browser opens, please CLICK inside the 'Start a post' text box.")
    print("⚠️ The script will wait 5 seconds and then paste the text for you.")
    print("Starting in 3 seconds... Press Ctrl+C to cancel.")
    time.sleep(3)
    
    # Mock parameters
    params = {
        # "topic": "Automating my life with Python and AI 🤖",
        "content": "Hello LinkedIn! This is a test post from my AI assistant. 🤖🚀\n\n#Python #AI #Automation"
    }
    
    # We pass None for player and session_memory as they are optional/handled
    create_linkedin_post(params, player=None)

if __name__ == "__main__":
    print("=== Jarvis Automation Test ===")
    
    # 1. Test TTS
    # test_tts_filtering() # Skipping TTS for now to focus on LinkedIn
    
    # 2. Test LinkedIn
    print("Starting LinkedIn test in 3 seconds...")
    time.sleep(3)
    test_linkedin_automation()
