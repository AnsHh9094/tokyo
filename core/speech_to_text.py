"""
Speech-to-Text module using Vosk (offline recognition).
Optimized for clean input: energy filtering, wake word, and noise rejection.
"""
import sounddevice as sd
import vosk
import queue
import sys
import json
import time
import struct
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VOSK_MODEL_PATH

# ── Configuration ─────────────────────────────────────────────
WAKE_WORDS = {"jarvis", "hey jarvis", "jarvis hey", "yo jarvis"}
ENERGY_THRESHOLD = 300        # Minimum audio amplitude to process
MIN_WORD_COUNT = 1            # Minimum words in recognized text
LISTEN_TIMEOUT = 30           # Seconds of silence before resetting
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000             # Smaller blocks = faster response

# ── Model loading ─────────────────────────────────────────────
_model = None


def get_model():
    """Lazy-load the Vosk model."""
    global _model
    if _model is None:
        model_path = VOSK_MODEL_PATH

        if not model_path.exists():
            common_paths = [
                Path.home() / "Downloads" / "vosk-model-small-en-us-0.15",
                Path.home() / "Downloads" / "vosk" / "vosk-model-small-en-us-0.15",
                Path("C:/vosk-model-small-en-us-0.15"),
            ]
            for p in common_paths:
                if p.exists():
                    model_path = p
                    break

        if not model_path.exists():
            print("=" * 60)
            print("❌ VOSK MODEL NOT FOUND!")
            print(f"   Expected at: {VOSK_MODEL_PATH}")
            print()
            print("   Download from: https://alphacephei.com/vosk/models")
            print("   Get: vosk-model-small-en-us-0.15")
            print(f"   Extract to: {VOSK_MODEL_PATH.parent}")
            print("=" * 60)
            raise FileNotFoundError(f"Vosk model not found at {VOSK_MODEL_PATH}")

        vosk.SetLogLevel(-1)
        _model = vosk.Model(str(model_path))
        print(f"✅ Vosk model loaded from {model_path}")

    return _model


# ── Audio queue ───────────────────────────────────────────────
_audio_queue = queue.Queue()
stop_listening_flag = threading.Event()


def _audio_callback(indata, frames, time_info, status):
    """Callback for sounddevice audio stream."""
    if status:
        print(f"⚠️ Audio: {status}", file=sys.stderr)
    _audio_queue.put(bytes(indata))


def _get_audio_energy(data: bytes) -> float:
    """Calculate RMS energy of audio chunk."""
    try:
        count = len(data) // 2
        if count == 0:
            return 0
        samples = struct.unpack(f"<{count}h", data)
        rms = (sum(s * s for s in samples) / count) ** 0.5
        return rms
    except Exception:
        return 0


def _flush_queue():
    """Clear any stale audio from the queue."""
    while not _audio_queue.empty():
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            break


# ── Voice recording ──────────────────────────────────────────
def record_voice(prompt="🎙 Listening...") -> str:
    """
    Blocking call: listens to microphone and returns recognized text.
    Filters out noise and requires minimum audio energy.
    Returns empty string if nothing meaningful recognized.
    """
    print(prompt)
    stop_listening_flag.clear()
    _flush_queue()

    try:
        model = get_model()
    except FileNotFoundError:
        return ""

    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype='int16',
            channels=1,
            callback=_audio_callback
        ):
            last_speech_time = time.time()

            while not stop_listening_flag.is_set():
                try:
                    data = _audio_queue.get(timeout=0.1)
                except queue.Empty:
                    # Check for timeout
                    if time.time() - last_speech_time > LISTEN_TIMEOUT:
                        _flush_queue()
                        rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
                        last_speech_time = time.time()
                    continue

                # Energy filter — skip silent/noise chunks
                energy = _get_audio_energy(data)
                if energy < ENERGY_THRESHOLD:
                    continue

                last_speech_time = time.time()

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()

                    if not text:
                        continue

                    # Filter garbage: too short or just noise words
                    words = text.split()
                    if len(words) < MIN_WORD_COUNT:
                        continue

                    # Filter common Vosk noise artifacts
                    noise_words = {"huh", "the", "a", "uh", "um", "ah",
                                   "oh", "eh", "hmm", "mm"}
                    if all(w.lower() in noise_words for w in words):
                        continue

                    print(f"👤 You: {text}")
                    return text

    except Exception as e:
        print(f"❌ Microphone error: {e}")
        print("   Make sure a microphone is connected.")
        return ""

    return ""


def stop_listening():
    """Signal the voice recorder to stop."""
    stop_listening_flag.set()
    _flush_queue()


def check_microphone() -> tuple:
    """Check if a microphone is available."""
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if input_devices:
            default = sd.query_devices(kind='input')
            return True, f"✅ Microphone: {default['name']}"
        else:
            return False, "❌ No microphone found"
    except Exception as e:
        return False, f"❌ Audio error: {e}"
