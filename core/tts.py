"""
Text-to-Speech module using Microsoft Edge TTS
Optimized for low latency: split-sentence streaming.
"""
import io
import re
import threading
import asyncio
import sounddevice as sd
import soundfile as sf
import edge_tts
import sys
import queue
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TTS_VOICE, TTS_RATE, TTS_VOLUME, TTS_PITCH

# ── Speaking state ────────────────────────────────────────────
stop_speaking_flag = threading.Event()
_is_speaking = threading.Event()
_audio_queue = queue.Queue()


def edge_speak(text: str, ui=None, blocking=False):
    """
    Speak text using Edge TTS with sentence-level streaming.
    Starts playing the first sentence while downloading the rest.
    """
    if not text or not text.strip():
        return

    # Remove emojis to prevent reading their names
    # Range covers most common emojis and symbols
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)


    # Split text into sentences for faster start
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return

    finished_event = threading.Event()

    def _producer_thread():
        """Download audio for each sentence in order."""
        _is_speaking.set()
        if ui:
            ui.start_speaking()
        
        stop_speaking_flag.clear()

        try:
            # Create a new loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            for sentence in sentences:
                if stop_speaking_flag.is_set():
                    break
                
                # Fetch audio for this sentence
                audio_data = loop.run_until_complete(_fetch_audio(sentence))
                if audio_data:
                    _audio_queue.put(audio_data)

            loop.close()
        except Exception as e:
            print(f"❌ TTS Download Error: {e}")
        finally:
            _audio_queue.put(None)  # Signal end of stream

    def _consumer_thread():
        """Play audio chunks as they arrive."""
        try:
            while not stop_speaking_flag.is_set():
                audio_data = _audio_queue.get()
                if audio_data is None:  # End of stream
                    break
                
                _play_audio(audio_data)
        except Exception as e:
            print(f"❌ Playback Error: {e}")
        finally:
            _is_speaking.clear()
            if ui:
                ui.stop_speaking()
            finished_event.set()

    # Start threads
    t_prod = threading.Thread(target=_producer_thread, daemon=True)
    t_cons = threading.Thread(target=_consumer_thread, daemon=True)
    
    t_prod.start()
    t_cons.start()

    if blocking:
        finished_event.wait()

import re as _re_detect  # For Hindi detection

# Hindi detection patterns
_HINDI_DEVANAGARI = _re_detect.compile(r'[\u0900-\u097F]')
_HINDI_ROMAN_WORDS = {
    'kya', 'hai', 'haan', 'nahi', 'bhai', 'yaar', 'acha', 'theek',
    'kaise', 'kaisa', 'kaha', 'kab', 'kyun', 'karo', 'bata', 'sun',
    'dekh', 'chal', 'bol', 'samajh', 'ruk', 'abhi', 'bahut', 'bilkul',
    'suno', 'mujhe', 'tumhe', 'humne', 'maine', 'tum', 'hum', 'mera',
    'tera', 'uska', 'woh', 'yeh', 'kuch', 'sab', 'aur', 'lekin',
    'karunga', 'gaya', 'gayi', 'raha', 'rahi', 'hoon', 'ho', 'hain'
}

def _detect_hindi(text: str) -> bool:
    """Detect if text is primarily Hindi."""
    if _HINDI_DEVANAGARI.search(text):
        return True
    words = text.lower().split()
    hindi_count = sum(1 for w in words if w.strip('.,!?') in _HINDI_ROMAN_WORDS)
    return hindi_count >= max(2, len(words) * 0.3)


async def _fetch_audio(text: str) -> bytes:
    """Fetch audio bytes for a single sentence with dynamic voice selection."""
    # Pick voice based on language
    voice = TTS_VOICE  # Default: en-GB-RyanNeural (JARVIS)
    if _detect_hindi(text):
        voice = "hi-IN-MadhurNeural"  # Male Hindi voice
    
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
        pitch=TTS_PITCH,
    )
    
    audio_bytes = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.write(chunk["data"])
            
    return audio_bytes.getvalue()


def _play_audio(data: bytes):
    """Decode and play a chunk of audio."""
    if stop_speaking_flag.is_set():
        return

    try:
        # Decode using soundfile
        with io.BytesIO(data) as f:
            audio_array, samplerate = sf.read(f, dtype="float32")
        
        # Play using sounddevice
        sd.play(audio_array, samplerate)
        sd.wait()  # Block until this chunk finishes
    except Exception as e:
        print(f"⚠️ Audio decode error: {e}")


def stop_speaking():
    """Immediately stop current speech."""
    stop_speaking_flag.set()
    sd.stop()
    # drain queue
    while not _audio_queue.empty():
        try: _audio_queue.get_nowait()
        except: break


def is_speaking() -> bool:
    """Check if Jarvis is currently speaking."""
    return _is_speaking.is_set()


async def list_voices(language="en"):
    """List available TTS voices for a language."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].startswith(language)]
