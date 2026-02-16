"""
Wake Word Listener — Passive background listener using Vosk (offline).
Listens continuously for a specific wake phrase like "wake up daddy's home".
Low resource usage since Vosk runs completely offline.
"""
import sounddevice as sd
import json
import threading
import time
import queue
import sys
from pathlib import Path

# Try to import Vosk
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("⚠️ Vosk not installed. Wake word detection disabled.")


class WakeWordListener:
    """
    Passive wake word listener using Vosk for offline speech recognition.
    Listens for specific phrases and triggers a callback when detected.
    """
    def __init__(self, on_wake_callback, model_path: str = None, 
                 wake_phrases: list = None, sample_rate: int = 16000):
        self.on_wake = on_wake_callback
        self.sample_rate = sample_rate
        self.running = False
        self.paused = False
        self.thread = None
        self._stop_event = threading.Event()
        self.model = None
        self.cooldown = 5.0  # Seconds between activations
        self._last_wake_time = 0
        
        # Default wake phrases (all lowercase for matching)
        self.wake_phrases = wake_phrases or [
            "wake up daddy's home",
            "wake up daddys home", 
            "daddy's home",
            "daddys home",
            "wake up",
            "wakeup",
            "jarvis",
            "hey jarvis",
            "hello jarvis",
            "wake up daddy is home",
        ]
        
        # Load Vosk model
        if VOSK_AVAILABLE and model_path:
            model_dir = Path(model_path)
            if model_dir.exists():
                try:
                    self.model = Model(str(model_dir))
                    print("✅ Wake Word Model loaded (Vosk)")
                except Exception as e:
                    print(f"❌ Failed to load Vosk model: {e}")
            else:
                print(f"⚠️ Vosk model not found at: {model_dir}")

    def start(self):
        """Start the wake word listener in a background thread."""
        if self.running or not self.model:
            if not self.model:
                print("⚠️ Wake Word Listener: No model loaded, skipping.")
            return
        
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("🎤 Wake Word Listener Started (listening for phrase...)")

    def stop(self):
        """Stop the listener."""
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
        print("🎤 Wake Word Listener Stopped")

    def pause(self):
        """Temporarily pause (e.g., when AI is speaking)."""
        self.paused = True

    def resume(self):
        """Resume listening."""
        self.paused = False

    def _check_for_wake_phrase(self, text: str) -> bool:
        """Check if the recognized text contains a wake phrase."""
        text_lower = text.lower().strip()
        for phrase in self.wake_phrases:
            if phrase in text_lower:
                return True
        return False

    def _listen_loop(self):
        """Main audio processing loop using shared AudioHub."""
        try:
            recognizer = KaldiRecognizer(self.model, self.sample_rate)
            recognizer.SetWords(False)  # Don't need word-level timestamps
            
            # Use a queue to receive audio from AudioHub
            audio_queue = queue.Queue(maxsize=50) # Buffer ~12.5s of audio

            # Register with AudioHub
            from core.audio_hub import audio_hub
            audio_hub.register(audio_queue)

            while not self._stop_event.is_set():
                if self.paused or not self.running:
                    time.sleep(0.1)
                    # Drain queue while paused to prevent old audio processing
                    while not audio_queue.empty():
                        try: audio_queue.get_nowait()
                        except: break
                    continue

                try:
                    data = audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "")
                    if text and self._check_for_wake_phrase(text):
                        now = time.time()
                        if now - self._last_wake_time > self.cooldown:
                            self._last_wake_time = now
                            print(f"🎤 Wake phrase detected: '{text}'") 
                            if self.on_wake:
                                self.on_wake()
                else:
                    # Check partial results too for faster detection
                    partial = json.loads(recognizer.PartialResult())
                    partial_text = partial.get("partial", "")
                    if partial_text and self._check_for_wake_phrase(partial_text):
                        now = time.time()
                        if now - self._last_wake_time > self.cooldown:
                            self._last_wake_time = now
                            print(f"🎤 Wake phrase detected (partial): '{partial_text}'")
                            if self.on_wake:
                                self.on_wake()
                            # Reset recognizer to prevent duplicate triggers
                            recognizer.Reset()

            # Cleanup
            audio_hub.unregister(audio_queue)

        except Exception as e:
            print(f"❌ Wake Word Listener Error: {e}")
            self.running = False
