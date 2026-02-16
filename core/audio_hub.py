"""
Centralized Audio Manager — Resolves microphone conflicts on Windows.
One single stream distributes audio to multiple consumers (Clap, Wake Word, Speech Rec).
"""
import sounddevice as sd
import threading
import queue
import time
import sys

# Audio format constants
SAMPLE_RATE = 16000
BLOCK_SIZE = 1600  # 100ms chunks (snappy for clap detection)
CHANNELS = 1
DTYPE = 'int16'

class AudioHub:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AudioHub, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
            
        self._consumers = []  # List of queues to send data to
        self._running = False
        self._thread = None
        self._stream = None
        self._initialized = True
        self.lock = threading.Lock()

    def start(self):
        """Start the shared audio stream if not already running."""
        with self.lock:
            if self._running:
                return
            
            self._running = True
            self._thread = threading.Thread(target=self._audio_loop, daemon=True)
            self._thread.start()
            print("🎤 AudioHub: Shared Stream Started")

    def stop(self):
        """Stop the shared audio stream."""
        with self.lock:
            self._running = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
            print("🎤 AudioHub: Shared Stream Stopped")

    def register(self, consumer_queue: queue.Queue):
        """Register a queue to receive audio chunks."""
        with self.lock:
            if consumer_queue not in self._consumers:
                self._consumers.append(consumer_queue)
                # print(f"🎤 AudioHub: New consumer registered (Total: {len(self._consumers)})")

    def unregister(self, consumer_queue: queue.Queue):
        """Unregister a queue."""
        with self.lock:
            if consumer_queue in self._consumers:
                self._consumers.remove(consumer_queue)
                # print(f"🎤 AudioHub: Consumer removed (Total: {len(self._consumers)})")

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback from sounddevice - distributes data to all consumers."""
        if status:
            print(f"⚠️ AudioHub Status: {status}", file=sys.stderr)
            
        if not self._running:
            return

        data = bytes(indata)
        
        # Distribute to all registered queues
        # We start a cleanup list for dead queues if any throw Full/Closed errors
        with self.lock:
            for q in self._consumers:
                try:
                    q.put_nowait(data)
                except queue.Full:
                    pass  # Consumer too slow, drop chunk
                except Exception:
                    pass  # Queue closed or other error

    def _audio_loop(self):
        """Main thread loop — keeps the stream alive with auto-recovery."""
        retries = 0
        while self._running and retries < 5:
            try:
                with sd.RawInputStream(
                    samplerate=SAMPLE_RATE,
                    blocksize=BLOCK_SIZE,
                    dtype=DTYPE,
                    channels=CHANNELS,
                    callback=self._audio_callback
                ) as stream:
                    self._stream = stream
                    retries = 0  # Reset on successful open
                    while self._running:
                        sd.sleep(100)
            except Exception as e:
                retries += 1
                print(f"❌ AudioHub Error (attempt {retries}/5): {e}")
                if self._running:
                    time.sleep(1.0)  # Wait before retry
        
        if retries >= 5:
            print("❌ AudioHub: Max retries reached, giving up")
            self._running = False

# Global singleton
audio_hub = AudioHub()
