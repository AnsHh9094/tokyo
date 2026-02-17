"""
Jarvis Voice Pack — Pre-recorded voice clips for ALL speech output.
This is the PRIMARY and ONLY voice system. No Edge TTS.
Maps actions, events, and phrases to .aif clips in voices/.
For dynamic AI text: plays an acknowledgment clip + shows text in UI.
"""
import os
import random
import threading
import aifc
import numpy as np
import sounddevice as sd
from pathlib import Path

# ── Voice Pack Directory ──────────────────────────────────────
VOICES_DIR = Path(__file__).parent.parent / "voices"

# ── Index: category → list of file paths ─────────────────────
_clips = {}
_loaded = False
_play_lock = threading.Lock()


def _index_clips():
    """Scan voices/ directory and categorize clips by naming convention."""
    global _loaded
    if _loaded or not VOICES_DIR.exists():
        return
    
    for f in VOICES_DIR.iterdir():
        if f.suffix.lower() not in ('.aif', '.aiff', '.wav'):
            continue
        
        # Strip "caged_" prefix to get category
        name = f.stem
        if name.startswith("caged_"):
            name = name[6:]
        
        # Group by base category (remove trailing _N number)
        parts = name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            category = parts[0]
        elif name.endswith("_m") or name.endswith("_s"):
            category = name[:-2]
        else:
            category = name
        
        if category not in _clips:
            _clips[category] = []
        _clips[category].append(f)
    
    _loaded = True
    total = sum(len(v) for v in _clips.values())
    print(f"🔊 Jarvis Voice: {total} clips in {len(_clips)} categories loaded")


def _pick_clip(category: str) -> Path | None:
    """Get a random clip from a category."""
    _index_clips()
    clips = _clips.get(category, [])
    return random.choice(clips) if clips else None


def _read_aiff(filepath: str) -> tuple:
    """Read AIFF file. Returns (samples_float32, samplerate)."""
    with aifc.open(str(filepath), 'rb') as f:
        n_channels = f.getnchannels()
        sampwidth = f.getsampwidth()
        framerate = f.getframerate()
        n_frames = f.getnframes()
        raw_data = f.readframes(n_frames)
    
    if sampwidth == 2:
        samples = np.frombuffer(raw_data, dtype='>i2').astype(np.float32) / 32768.0
    elif sampwidth == 1:
        samples = np.frombuffer(raw_data, dtype=np.int8).astype(np.float32) / 128.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")
    
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels)
    
    return samples, framerate


def play_clip(category: str, blocking=True) -> bool:
    """Play a random clip from a category. Returns True if played."""
    clip = _pick_clip(category)
    if not clip:
        return False
    
    try:
        with _play_lock:
            samples, sr = _read_aiff(str(clip))
            sd.play(samples, sr)
            if blocking:
                sd.wait()
    except Exception as e:
        print(f"⚠️ Clip error ({clip.name}): {e}")
        return False
    return True


def play_clip_async(category: str) -> bool:
    """Play clip in background thread."""
    clip = _pick_clip(category)
    if not clip:
        return False
    
    def _play():
        try:
            with _play_lock:
                samples, sr = _read_aiff(str(clip))
                sd.play(samples, sr)
                sd.wait()
        except Exception as e:
            print(f"⚠️ Clip error ({clip.name}): {e}")
    
    threading.Thread(target=_play, daemon=True).start()
    return True


# ══════════════════════════════════════════════════════════════
#  COMPREHENSIVE PHRASE → CATEGORY MAPPING
#  Covers all standard Jarvis interactions
# ══════════════════════════════════════════════════════════════

_PHRASE_MAP = {
    # ── Greetings / Wake-up ────────────────────
    "at your service": "listening_on",
    "i'm here": "listening_on",
    "how can i help": "listening_on",
    "what do you need": "listening_on",
    "listening": "listening_on",
    "yes sir": "listening_on",
    "ready": "listening_on",
    "standing by": "listening_on",
    "good morning": "listening_on_morning",
    "good afternoon": "listening_on_afternoon",
    "good evening": "listening_on_evening",
    "good night": "goodnight",
    "sleep well": "goodnight",
    
    # ── System states ─────────────────────────
    "systems online": "activated",
    "activated": "activated",
    "online": "activated",
    "booting up": "activated",
    "initializing": "activated",
    "powering down": "power_down",
    "shutting down": "power_down",
    "goodbye": "power_down",
    "signing off": "power_down",
    "self destruct": "self_destruct",
    
    # ── Acknowledgments / Confirmations ────────
    "on it": "listening_on",
    "right away": "listening_on",
    "done": "message_sent",
    "completed": "message_sent",
    "finished": "message_sent",
    "got it": "listening_on",
    "understood": "listening_on",
    "certainly": "listening_on",
    "of course": "listening_on",
    
    # ── Messages ──────────────────────────────
    "message sent": "message_sent",
    "sent": "message_sent",
    "sending message": "message_sending",
    "sending": "message_sending",
    "new message": "message_new",
    "you have a message": "message_new",
    "email": "message_email",
    "checking email": "message_email_check",
    "new email": "message_email_new",
    "email sent": "message_email_sent",
    "meeting": "message_meeting",
    "voicemail": "message_voicemail",
    "text message": "message_text",
    "cancelled": "messages_cancelled",
    
    # ── Media ─────────────────────────────────
    "playing": "media_play",
    "now playing": "media_play",
    "music": "media_play",
    "play": "media_play",
    "accessing media": "media_accessing",
    "accessing": "media_accessing",
    
    # ── Phone / Calls ─────────────────────────
    "calling": "ringtone_call",
    "incoming call": "ringtone_call",
    "call": "ringtone_call",
    "dialing": "ringtone_accessing",
    
    # ── Battery ───────────────────────────────
    "battery charged": "battery_charged",
    "fully charged": "battery_charged",
    "battery low": "battery_low",
    "low battery": "battery_low",
    "charging": "battery_charging",
    
    # ── Network ───────────────────────────────
    "wifi": "activate_wifi",
    "no wifi": "network_no_wifi",
    "connection lost": "network_lost_wifi",
    "network lost": "network_lost_wifi",
    "no internet": "network_no_wifi",
    
    # ── Schedule / Time ───────────────────────
    "schedule": "schedule",
    "your schedule": "schedule",
    "no events": "schedule_none",
    "no schedule": "schedule_none",
    "reminder": "20sec_reminder",
    "alarm": "30sec_alarm",
    "timer": "30sec_alarm",
    
    # ── Location ──────────────────────────────
    "location": "location",
    "where": "location",
    
    # ── Settings / Help ───────────────────────
    "settings": "settings_help",
    "help": "settings_help",
    "adjusting": "bd_adjusting",
    
    # ── Didn't understand ─────────────────────
    "repeat": "repeat",
    "say that again": "repeat",
    "didn't catch": "repeat",
    "pardon": "repeat",
    "didn't understand": "repeat",
    "come again": "repeat",
    "couldn't hear": "repeat",
    "sorry": "repeat",
    "i didn't get": "repeat",
    
    # ── Searching / Processing ────────────────
    "searching": "media_accessing",
    "processing": "media_accessing",
    "looking": "media_accessing",
    "analyzing": "media_accessing",
    "scanning": "media_accessing",
    "loading": "media_accessing",
    
    # ── Image / Content ───────────────────────
    "generating": "media_accessing",
    "creating": "media_accessing",
    "image": "media_accessing",
    "here is": "accessed",
    "found": "accessed",
    "result": "accessed",
    "here you go": "accessed",
    
    # ── Opening apps ──────────────────────────
    "opening": "media_accessing",
    "launching": "media_accessing",
    "open": "media_accessing",
    
    # ── Errors ────────────────────────────────
    "error": "repeat",
    "failed": "repeat",
    "couldn't": "repeat",
    "unable": "repeat",
    "problem": "repeat",
    
    # ── Questions ─────────────────────────────
    "what should": "ask",
    "which one": "ask",
    "clarif": "ask",
    "specify": "ask",
    
    # ── Clipboard / Screenshot ────────────────
    "copied": "message_sent",
    "clipboard": "message_sent",
    "screenshot": "accessed",
    "captured": "accessed",
    
    # ── Volume ────────────────────────────────
    "volume": "bd_adjusting",
    "adjusting volume": "bd_adjusting",
    
    # ── LinkedIn / Content posting ────────────
    "posting": "message_sending",
    "post": "message_sending",
    "drafting": "media_accessing",
    "preparing": "media_accessing",
    "pasting": "message_sending",
    "pasted": "message_sent",
    "published": "message_sent",
    "linkedin": "message_sending",
    
    # ── Spotify ───────────────────────────────
    "spotify": "media_play",
    "youtube": "media_play",
    "song": "media_play",
    "track": "media_play",
    "next": "media_play",
    "previous": "media_play",
    "pause": "bd_pause",
    "paused": "bd_pause",
    
    # ── Weather ───────────────────────────────
    "weather": "accessed",
    "temperature": "accessed",
    "forecast": "accessed",
    
    # ── System info ───────────────────────────
    "cpu": "accessed",
    "ram": "accessed",
    "disk": "accessed",
    "system info": "accessed",
    
    # ── Notes ─────────────────────────────────
    "note saved": "message_sent",
    "noted": "message_sent",
    "note": "message_sent",
}

# Sorted by longest phrase first so longer matches take priority
_SORTED_PHRASES = sorted(_PHRASE_MAP.keys(), key=len, reverse=True)


def try_speak_clip(text: str) -> bool:
    """
    Try to play a pre-recorded Jarvis voice clip matching the text.
    Returns True if a clip was played.
    """
    _index_clips()
    if not text or not _clips:
        return False
    
    text_lower = text.lower().strip()
    
    # Check phrase map (longest match first)
    for phrase in _SORTED_PHRASES:
        if phrase in text_lower:
            category = _PHRASE_MAP[phrase]
            if play_clip(category, blocking=True):
                return True
    
    # No specific match — play a generic acknowledgment
    # for any text that looks like a response
    if len(text_lower) > 5:
        # Use "listening_on" as generic acknowledgment
        return play_clip("listening_on", blocking=True)
    
    return False


def try_speak_clip_async(text: str) -> bool:
    """Non-blocking version — play matching clip in background."""
    _index_clips()
    if not text or not _clips:
        return False
    
    text_lower = text.lower().strip()
    
    for phrase in _SORTED_PHRASES:
        if phrase in text_lower:
            category = _PHRASE_MAP[phrase]
            return play_clip_async(category)
    
    return False


# ── Convenience functions ─────────────────────────────────────

def play_button_sound():
    play_clip_async("button_sound")

def play_process_sound():
    play_clip_async("button_sound_process")

def play_mic_sound():
    play_clip_async("button_sound_mic")

def play_greeting():
    """Play a contextual greeting based on time of day."""
    from datetime import datetime
    hour = datetime.now().hour
    if 5 <= hour < 12:
        if not play_clip("listening_on_morning"):
            play_clip("listening_on")
    elif 12 <= hour < 17:
        if not play_clip("listening_on_afternoon"):
            play_clip("listening_on")
    elif 17 <= hour < 21:
        if not play_clip("listening_on_evening"):
            play_clip("listening_on")
    else:
        play_clip("listening_on")


def get_categories() -> dict:
    """Return all categories and clip counts (for debugging)."""
    _index_clips()
    return {k: len(v) for k, v in sorted(_clips.items())}


# ── Auto-index on import ─────────────────────────────────────
_index_clips()
