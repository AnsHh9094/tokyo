"""
TTS Engine — ElevenLabs dual-voice system with Edge TTS fallback.

Voices:
  - English: ElevenLabs voice auq43ws1oslv0tO4BDa7
  - Hindi:   ElevenLabs voice jUjRbhZWoMK4aDciW36V
  - Fallback: Edge TTS (en-GB-RyanNeural) if ElevenLabs is down/quota exceeded
"""
import re
import os
import io
import threading
import tempfile
import requests
import sounddevice as sd
import soundfile as sf

import json
from pathlib import Path

from config import ELEVENLABS_API_KEY

# ── Config ────────────────────────────────────────────────────


# Voice IDs from ElevenLabs Voice Library
VOICE_ENGLISH = "auq43ws1oslv0tO4BDa7"
VOICE_HINDI = "jUjRbhZWoMK4aDciW36V"

# Edge TTS fallback voice
EDGE_TTS_VOICE = "en-GB-RyanNeural"
EDGE_TTS_RATE = "-5%"
EDGE_TTS_PITCH = "-3Hz"

# ElevenLabs API endpoint
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# ── Speaking state ────────────────────────────────────────────
stop_speaking_flag = threading.Event()
_is_speaking = threading.Event()

# Hindi character detection ranges
_HINDI_PATTERN = re.compile(r'[\u0900-\u097F\u0980-\u09FF\uA8E0-\uA8FF]')

# Common Hindi words written in English (Romanized Hindi)
_HINDI_WORDS = {
    'kya', 'hai', 'kaise', 'ho', 'haan', 'nahi', 'theek', 'accha',
    'acha', 'bhai', 'yaar', 'karo', 'karna', 'batao', 'bolo', 'sunao',
    'dekho', 'chalo', 'ruk', 'bas', 'bohot', 'bahut', 'zyada', 'kam',
    'mujhe', 'tujhe', 'humko', 'tumko', 'unko', 'isko', 'usko',
    'kaha', 'kab', 'kyun', 'kaun', 'konsa', 'kitna', 'kidhar',
    'abhi', 'baad', 'pehle', 'phir', 'lekin', 'aur', 'ya', 'par',
    'mein', 'hum', 'tum', 'woh', 'yeh', 'ye', 'wo', 'ji', 'sahab',
    'sir', 'baat', 'suno', 'bata', 'bol', 'samjha', 'samjhe',
    'dhanyawad', 'shukriya', 'namaste', 'alvida', 'thik',
    'nai', 'mat', 'raha', 'rahi', 'rahe', 'gaya', 'gayi', 'gaye',
    'chahiye', 'sakta', 'sakti', 'sakte', 'wala', 'wali', 'wale',
    'kuch', 'sab', 'bilkul', 'zaroor', 'pakka', 'hoga', 'hogi',
}


def _detect_language(text: str) -> str:
    """
    Detect if text is Hindi or English.
    Returns 'hi' for Hindi, 'en' for English.
    """
    # Check for Devanagari script
    if _HINDI_PATTERN.search(text):
        return 'hi'

    # Check for romanized Hindi words
    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    hindi_count = len(words & _HINDI_WORDS)
    if len(words) > 0 and hindi_count / len(words) > 0.3:
        return 'hi'

    return 'en'


def _speak_elevenlabs(text: str, voice_id: str) -> bool:
    """
    Generate speech using ElevenLabs API.
    Returns True if successful, False otherwise.
    """
    url = f"{ELEVENLABS_API_URL}/{voice_id}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        if response.status_code == 200 and len(response.content) > 1000:
            # Play the audio directly from memory
            audio_data, sample_rate = sf.read(io.BytesIO(response.content))

            if stop_speaking_flag.is_set():
                return True

            sd.play(audio_data, sample_rate)
            sd.wait()
            return True
        else:
            print(f"⚠️ ElevenLabs: HTTP {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⚠️ ElevenLabs: timeout")
        return False
    except Exception as e:
        print(f"⚠️ ElevenLabs: {e}")
        return False


def _speak_edge_tts(text: str) -> bool:
    """
    Fallback: Use Microsoft Edge TTS (free, no API key).
    Returns True if successful.
    """
    try:
        import edge_tts
        import asyncio

        async def _generate_and_play():
            communicate = edge_tts.Communicate(
                text,
                voice=EDGE_TTS_VOICE,
                rate=EDGE_TTS_RATE,
                pitch=EDGE_TTS_PITCH,
            )

            # Collect all audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if stop_speaking_flag.is_set():
                    return True
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            if audio_chunks and not stop_speaking_flag.is_set():
                full_audio = b"".join(audio_chunks)
                # Save to temp file and play
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(full_audio)
                    temp_path = f.name

                try:
                    audio_data, sample_rate = sf.read(temp_path)
                    sd.play(audio_data, sample_rate)
                    sd.wait()
                finally:
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            return True

        # Run async in a new event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_generate_and_play())
        finally:
            loop.close()
        return True

    except ImportError:
        print("⚠️ edge-tts not installed, cannot fallback")
        return False
    except Exception as e:
        print(f"⚠️ Edge TTS fallback: {e}")
        return False


def edge_speak(text: str, ui=None, blocking=False):
    """
    Speak text using ElevenLabs (primary) or Edge TTS (fallback).
    
    Auto-detects language:
    - Hindi text → Hindi ElevenLabs voice
    - English text → English ElevenLabs voice
    - If ElevenLabs fails → Edge TTS British Ryan voice
    
    Function name kept as edge_speak for backward compatibility.
    """
    if not text or not text.strip():
        return

    # Remove emojis and clean text
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text).strip()
    # Remove emoji names like :fire: :sparkles:
    text = re.sub(r':[a-z_]+:', '', text).strip()
    if not text:
        return

    stop_speaking_flag.clear()

    def _speak():
        _is_speaking.set()
        if ui:
            try:
                ui.start_speaking()
            except:
                pass

        try:
            # Detect language and pick voice
            lang = _detect_language(text)
            voice_id = VOICE_HINDI if lang == 'hi' else VOICE_ENGLISH

            print(f"🔊 Speaking ({lang}): {text[:50]}...")

            # Try ElevenLabs first
            success = _speak_elevenlabs(text, voice_id)

            # Fallback to Edge TTS if ElevenLabs fails
            if not success and not stop_speaking_flag.is_set():
                print("🔄 Falling back to Edge TTS...")
                _speak_edge_tts(text)

        except Exception as e:
            print(f"⚠️ TTS error: {e}")
        finally:
            _is_speaking.clear()
            if ui:
                try:
                    ui.stop_speaking()
                except:
                    pass

    if blocking:
        _speak()
    else:
        threading.Thread(target=_speak, daemon=True).start()


def stop_speaking():
    """Immediately stop current speech."""
    stop_speaking_flag.set()
    sd.stop()


def is_speaking() -> bool:
    """Check if currently speaking."""
    return _is_speaking.is_set()
