"""
Text-to-Speech module using Microsoft Edge TTS
High-quality, free, neural TTS with multiple voices.
"""
import io
import threading
import asyncio
import sounddevice as sd
import soundfile as sf
import edge_tts
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TTS_VOICE, TTS_RATE, TTS_VOLUME, TTS_PITCH

# ── Speaking state ────────────────────────────────────────────
stop_speaking_flag = threading.Event()
_is_speaking = threading.Event()


def edge_speak(text: str, ui=None, blocking=False):
    """
    Speak text using Edge TTS.

    Args:
        text: Text to speak
        ui: JarvisUI instance for visual feedback
        blocking: If True, wait until speech completes
    """
    if not text or not text.strip():
        return

    finished_event = threading.Event()

    def _thread():
        _is_speaking.set()

        if ui:
            ui.start_speaking()

        stop_speaking_flag.clear()

        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_speak_async(text))
            loop.close()
        except Exception as e:
            print(f"❌ TTS Error: {e}")
        finally:
            _is_speaking.clear()
            if ui:
                ui.stop_speaking()
            finished_event.set()

    t = threading.Thread(target=_thread, daemon=True)
    t.start()

    if blocking:
        finished_event.wait()


async def _speak_async(text: str):
    """Internal async TTS implementation."""
    communicate = edge_tts.Communicate(
        text=text.strip(),
        voice=TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
        pitch=TTS_PITCH,
    )

    audio_bytes = io.BytesIO()

    async for chunk in communicate.stream():
        if stop_speaking_flag.is_set():
            return

        if chunk["type"] == "audio":
            audio_bytes.write(chunk["data"])

    if audio_bytes.tell() == 0:
        return

    audio_bytes.seek(0)

    try:
        data, samplerate = sf.read(audio_bytes, dtype="float32")
    except Exception as e:
        print(f"⚠️ Audio decode error: {e}")
        return

    channels = data.shape[1] if len(data.shape) > 1 else 1

    try:
        with sd.OutputStream(
            samplerate=samplerate,
            channels=channels,
            dtype="float32",
        ) as stream:
            block_size = 1024
            for start in range(0, len(data), block_size):
                if stop_speaking_flag.is_set():
                    break
                stream.write(data[start:start + block_size])
    except Exception as e:
        print(f"❌ Audio playback error: {e}")


def stop_speaking():
    """Immediately stop current speech."""
    stop_speaking_flag.set()


def is_speaking() -> bool:
    """Check if Jarvis is currently speaking."""
    return _is_speaking.is_set()


async def list_voices(language="en"):
    """List available TTS voices for a language."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].startswith(language)]
