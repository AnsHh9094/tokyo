import pyautogui
import time
import sys
import os

def test_sequence(seq_num):
    print(f"Testing Sequence #{seq_num}...")
    
    # 1. Open Spotify Search
    print("   Opening Spotify...")
    os.startfile("spotify:search:sicko mode")
    time.sleep(3.5) # Wait for load
    
    # 2. Execute Sequence
    if seq_num == 1:
        print("   Seq 1: Tab -> Tab -> Enter")
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("enter")
        
    elif seq_num == 2:
        print("   Seq 2: Tab -> Enter")
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("enter")

    elif seq_num == 3:
        print("   Seq 3: Ctrl+A -> Tab -> Enter")
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.5)
        pyautogui.press("tab")
        time.sleep(0.5)
        pyautogui.press("enter")

    elif seq_num == 4:
        print("   Seq 4: Tab -> Tab -> Tab -> Enter")
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.press("tab")
        time.sleep(0.3)
        pyautogui.press("enter")
        
    print("Done. Did it play?")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_sequence(int(sys.argv[1]))
    else:
        print("Run with a sequence number: python debug_spotify_keys.py 1")
        print("1: Tab -> Tab -> Enter")
        print("2: Tab -> Enter")
        print("3: Ctrl+A -> Tab -> Enter")
        print("4: Tab -> Tab -> Tab -> Enter")
