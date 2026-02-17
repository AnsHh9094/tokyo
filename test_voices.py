"""Test ElevenLabs API key using config."""
import requests
import json
from pathlib import Path

# Load key from config
try:
    config_path = Path(__file__).parent / "config" / "api_keys.json"
    with open(config_path, "r") as f:
        data = json.load(f)
        API_KEY = data.get("elevenlabs_api_key", "")
except Exception as e:
    print(f"Failed to load config: {e}")
    API_KEY = ""

print(f"Using Key: {API_KEY[:8]}...{API_KEY[-4:] if API_KEY else ''}")
HEADERS = {"xi-api-key": API_KEY}

# Test 1: User Info (Authentication Check)
print("\n--- 1. Authentication Check (Get User Info) ---")
try:
    r = requests.get("https://api.elevenlabs.io/v1/user", headers=HEADERS, timeout=10)
    print(f"HTTP {r.status_code}")
    if r.status_code == 200:
        user = r.json()
        sub = user.get('subscription', {})
        print(f"✅ Authenticated as: {user.get('first_name')}")
        print(f"   Quota: {sub.get('character_count', 0)} / {sub.get('character_limit', 0)} used")
    else:
        print(f"❌ Auth Failed: {r.text}")
except Exception as e:
    print(f"❌ Request Error: {e}")

# Test 2: Voice Availability Check
print("\n--- 2. Voice Availability ---")
TARGET_VOICES = ["auq43ws1oslv0tO4BDa7", "jUjRbhZWoMK4aDciW36V"]
try:
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        available_ids = {v['voice_id'] for v in r.json().get('voices', [])}
        for vid in TARGET_VOICES:
            if vid in available_ids:
                print(f"✅ Voice {vid} found in your library")
            else:
                print(f"❌ Voice {vid} NOT found (Needs to be added to VoiceLab)")
    else:
        print("Skipped (Auth failed)")
except Exception as e:
    print(f"Error: {e}")
