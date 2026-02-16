"""
Speech-to-Text module using Google Speech Recognition (Online).
Optimized for Hinglish support and accuracy.
Uses sounddevice for efficient VAD and buffering.
"""
import sounddevice as sd
import speech_recognition as sr
import queue
import sys
import time
import struct
import threading
import io
import wave
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────
SAMPLE_RATE = 16000
BLOCK_SIZE = 2000             # 125ms updates
DEFAULT_THRESHOLD = 150       # Fallback energy threshold (lowered for better pickup)
SILENCE_DURATION = 1.2        # Seconds of silence to consider "done speaking"
MAX_RECORD_TIME = 15.0        # Max seconds to record one command
CALIBRATION_FRAMES = 5        # Frames to measure ambient noise (reduced for faster response)

# ── Audio queue ───────────────────────────────────────────────
_audio_queue = queue.Queue()
stop_listening_flag = threading.Event()
recognizer = sr.Recognizer()

def _get_energy(data: bytes) -> float:
    """Calculate RMS energy."""
    try:
        count = len(data) // 2
        if count == 0: return 0
        samples = struct.unpack(f"<{count}h", data)
        rms = (sum(s * s for s in samples) / count) ** 0.5
        return rms
    except:
        return 0

def _flush_queue():
    while not _audio_queue.empty():
        try: _audio_queue.get_nowait()
        except queue.Empty: break

# ── Voice recording ──────────────────────────────────────────
def record_voice(prompt="🎙 Listening...") -> str:
    """
    Listens for speech using shared AudioHub stream.
    Supports Hinglish (en-IN) and mixed inputs accurately.
    """
    # Verify AudioHub is running (it should be started by main)
    from core.audio_hub import audio_hub
    
    print(prompt)
    stop_listening_flag.clear()
    _flush_queue()
    
    # Register our queue with the hub
    audio_hub.register(_audio_queue)

    # 1. Dynamic Calibration
    threshold = DEFAULT_THRESHOLD
    try:
        energy_levels = []
        for _ in range(CALIBRATION_FRAMES):
            if stop_listening_flag.is_set(): 
                audio_hub.unregister(_audio_queue)
                return ""
            try:
                data = _audio_queue.get(timeout=0.2)
                energy_levels.append(_get_energy(data))
            except: pass
        
        if energy_levels:
            avg_noise = sum(energy_levels) / len(energy_levels)
            threshold = max(DEFAULT_THRESHOLD, avg_noise * 1.5)
    except Exception as e:
        print(f"❌ calibration error: {e}")
        # threshold remains default

    # 2. Listening & Buffering
    print(f"🎤 Speak now (Threshold: {threshold:.0f})...")
    
    frames_since_speech = 0
    speech_detected = False
    start_time = time.time()
    
    audio_buffer = io.BytesIO()
    has_content = False

    try:
        while not stop_listening_flag.is_set():
            # Timeout
            if time.time() - start_time > MAX_RECORD_TIME:
                break

            try:
                data = _audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            energy = _get_energy(data)
            
            # Check for speech start
            if energy > threshold:
                speech_detected = True
                frames_since_speech = 0
            elif speech_detected:
                # Silence after speech
                frames_since_speech += 1
            
            # Buffer audio if speech detected or recently active
            if speech_detected:
                audio_buffer.write(data)
                has_content = True
                
                # Silence detection end
                silence_sec = (frames_since_speech * BLOCK_SIZE) / SAMPLE_RATE
                if silence_sec > SILENCE_DURATION:
                    break  # Done speaking
                    
    except Exception as e:
        print(f"❌ Voice Loop Error: {e}")
    finally:
        audio_hub.unregister(_audio_queue)

    if not has_content:
        return ""

    # 3. Transcribe with Google
    # print("🧠 Recognizing...")
    try:
        raw_data = audio_buffer.getvalue()
        # AudioHub provides 16000Hz mono int16
        audio_data = sr.AudioData(raw_data, SAMPLE_RATE, 2)  # 2 bytes width = int16
        
        # Recognize with Hindi/India preference for Hinglish
        text = recognizer.recognize_google(audio_data, language="en-IN")
        print(f"👤 You: {text}")
        return text
    except sr.UnknownValueError:
        # print("❌ Could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"❌ Google API Error: {e}")
        return ""
    except Exception as e:
        print(f"❌ Recognition Error: {e}")
        return ""

def stop_listening():
    stop_listening_flag.set()
    _flush_queue()

def check_microphone() -> tuple:
    try:
        default = sd.query_devices(kind='input')
        return True, f"✅ Mic: {default['name']}"
    except:
        return False, "❌ No Mic Found"
