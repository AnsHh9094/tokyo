import time
import pyautogui
import os

def test_spotify():
    print("Testing Spotify Control...")
    query = "Blinding Lights"
    
    print(f"1. Opening Spotify search for '{query}'...")
    os.startfile(f"spotify:search:{query}")
    
    time.sleep(3)
    
    print("2. Attempting to play top result...")
    # Sequence A: Tab -> Enter
    print("   Pressing TAB...")
    pyautogui.press("tab")
    time.sleep(0.5)
    print("   Pressing ENTER...")
    pyautogui.press("enter")
    
    time.sleep(5)
    
    print("3. Testing Pause (Global Key)...")
    pyautogui.press("playpause")
    
if __name__ == "__main__":
    test_spotify()
