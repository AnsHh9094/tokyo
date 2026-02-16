import sounddevice as sd
import numpy as np
import os
import time
import psutil
import subprocess
import sys
from pathlib import Path

# Configuration
CLAP_THRESHOLD = 15  # Lowered threshold further
COOLDOWN = 1.0       # Seconds between checks
PROJECT_DIR = Path(__file__).parent
BAT_FILE = PROJECT_DIR / "Run_Tokyo_Silent.bat"

def is_jarvis_running():
    """Check if main.py is already running."""
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            if p.info['name'] and 'python' in p.info['name'].lower():
                if p.info['cmdline'] and any('main.py' in arg for arg in p.info['cmdline']):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def launch_jarvis():
    """Launch the assistant."""
    print("\n🚀 CLAP DETECTED! Launching Tokyo...")
    # Launch completely detached/silent
    subprocess.Popen([str(BAT_FILE)], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

def audio_callback(indata, frames, time, status):
    """Real-time audio processing."""
    if status:
        print(status)
    
    # Calculate volume (Root Mean Square)
    volume_norm = np.linalg.norm(indata) * 10
    
    # Visual feedback for debugging
    bar = "|" * int(volume_norm)
    if int(volume_norm) > 1:
        print(f"Volume: {int(volume_norm)} {bar}")

    if volume_norm > CLAP_THRESHOLD:
        if not is_jarvis_running():
            launch_jarvis()
            # Wait a bit to prevent multiple launches from one clap sequence
            sd.sleep(5000)
        else:
            print("Already running.")
            sd.sleep(2000)

if __name__ == "__main__":
    print(f"👏 Clap Listener Active (Threshold: {CLAP_THRESHOLD})")
    print("Listening for claps...")

    try:
        # Check for numpy
        if 'numpy' not in sys.modules:
            import numpy as np

        with sd.InputStream(callback=audio_callback, channels=1, samplerate=44100):
            while True:
                time.sleep(1.0)
                
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"\nError: {e}")
