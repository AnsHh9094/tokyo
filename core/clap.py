"""
Optimized Double-Clap Listener — Uses native C extension for audio analysis.
Falls back to a lightweight pure-Python path if the DLL is not available.

Detection pipeline:
  1. RMS energy above adaptive noise floor
  2. Sharp transient onset (energy jump from previous frame)
  3. High-frequency energy ratio (broadband = clap, low-freq = speech/music)
"""
import sounddevice as sd
import threading
import time
import queue
import sys
import ctypes
import struct
import math
from pathlib import Path

# ── Try to load C extension ──────────────────────────────────
_native = None
_HERE = Path(__file__).parent

def _load_native():
    """Attempt to load the compiled C extension."""
    global _native
    dll_path = _HERE / "clap_native.dll"
    if not dll_path.exists():
        return False
    try:
        lib = ctypes.CDLL(str(dll_path))
        # int analyze_clap(float*, int, int, float, float, float,
        #                  float, float, float, float, float*, float*)
        lib.analyze_clap.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # samples
            ctypes.c_int,                     # n_samples
            ctypes.c_int,                     # samplerate
            ctypes.c_float,                   # threshold
            ctypes.c_float,                   # noise_floor
            ctypes.c_float,                   # clap_ratio
            ctypes.c_float,                   # prev_energy
            ctypes.c_float,                   # onset_ratio
            ctypes.c_float,                   # hf_ratio_min
            ctypes.c_float,                   # noise_alpha
            ctypes.POINTER(ctypes.c_float),   # out_energy
            ctypes.POINTER(ctypes.c_float),   # out_new_noise
        ]
        lib.analyze_clap.restype = ctypes.c_int
        _native = lib
        return True
    except Exception as e:
        print(f"⚠️ Could not load clap_native.dll: {e}")
        return False

_HAS_NATIVE = _load_native()

# ── Optional numpy import (only for fallback) ────────────────
_np = None
if not _HAS_NATIVE:
    try:
        import numpy as _np
    except ImportError:
        pass


class ClapListener:
    """
    High-performance Double-Clap Listener.
    Uses native C extension when available, falls back to pure Python.
    """

    def __init__(self, on_clap_callback, threshold=15,
                 double_clap_min=0.12, double_clap_max=0.65, cooldown=2.0):
        self.on_clap = on_clap_callback
        self.threshold = threshold
        self.double_clap_min = double_clap_min
        self.double_clap_max = double_clap_max
        self.cooldown = cooldown
        self.running = False
        self.paused = False
        self._first_clap_time = 0
        self._last_trigger_time = 0
        self.thread = None
        self._stop_event = threading.Event()

        # Adaptive noise floor
        self._noise_floor = 2.0
        self._noise_alpha = 0.02
        self._clap_ratio = 4.0

        # Transient detection
        self._prev_energy = 0.0
        self._onset_ratio = 6.0

        # Spectral thresholds
        self._hf_ratio_min = 0.30
        self._samplerate = 16000  # Must match AudioHub

        # Debounce
        self._last_peak_time = 0
        self._debounce = 0.06

        mode = "NATIVE C" if _HAS_NATIVE else ("NUMPY" if _np else "PURE PYTHON")
        print(f"👏 Clap Detector Mode: {mode}")

    def start(self):
        """Start the listener in a background thread."""
        if self.running:
            return
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("👏 Double-Clap Listener Started")

    def stop(self):
        """Stop the listener."""
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)
        print("👏 Double-Clap Listener Stopped")

    def pause(self):
        """Temporarily pause listening."""
        self.paused = True

    def resume(self):
        """Resume listening."""
        self.paused = False
        self._first_clap_time = 0
        self._prev_energy = 0.0

    # ── Native C path ────────────────────────────────────────
    def _is_clap_native(self, indata):
        """Analyze audio block using the C extension. Zero numpy dependency."""
        # Convert sounddevice float32 buffer to ctypes array
        raw = bytes(indata)
        n_samples = len(raw) // 4  # float32 = 4 bytes
        arr = (ctypes.c_float * n_samples).from_buffer_copy(raw)

        out_energy = ctypes.c_float(0.0)
        out_noise = ctypes.c_float(0.0)

        result = _native.analyze_clap(
            arr, n_samples, self._samplerate,
            ctypes.c_float(self.threshold),
            ctypes.c_float(self._noise_floor),
            ctypes.c_float(self._clap_ratio),
            ctypes.c_float(self._prev_energy),
            ctypes.c_float(self._onset_ratio),
            ctypes.c_float(self._hf_ratio_min),
            ctypes.c_float(self._noise_alpha),
            ctypes.byref(out_energy),
            ctypes.byref(out_noise),
        )

        energy = out_energy.value
        self._noise_floor = out_noise.value
        self._prev_energy = energy

        return bool(result), energy

    # ── Pure Python fallback (no numpy needed) ───────────────
    def _is_clap_pure(self, indata):
        """Lightweight pure-Python clap detection — energy + onset only, no FFT."""
        raw = bytes(indata)
        n_samples = len(raw) // 4
        # Unpack float32 samples
        samples = struct.unpack(f'<{n_samples}f', raw)

        # RMS energy
        sum_sq = 0.0
        for s in samples:
            sum_sq += s * s
        energy = math.sqrt(sum_sq / n_samples) * 100.0

        # Above noise floor
        above_noise = energy > (self._noise_floor * self._clap_ratio) and energy > self.threshold

        # Transient onset
        if self._prev_energy > 0.01:
            onset = (energy / max(self._prev_energy, 0.01)) > self._onset_ratio
        else:
            onset = energy > self.threshold * 2

        # Update state
        self._prev_energy = energy
        if energy < self.threshold * 0.5:
            self._noise_floor = (1 - self._noise_alpha) * self._noise_floor + self._noise_alpha * energy

        # Skip FFT in pure Python mode — energy + onset is sufficient
        # for most environments. Slightly higher false positive rate.
        return (above_noise and onset), energy

    # ── Numpy fallback (original logic) ──────────────────────
    def _is_clap_numpy(self, indata):
        """Fallback using numpy (original algorithm)."""
        energy = float(_np.sqrt(_np.mean(indata ** 2)) * 100)
        above_noise = energy > (self._noise_floor * self._clap_ratio) and energy > self.threshold

        if self._prev_energy > 0.01:
            onset = (energy / max(self._prev_energy, 0.01)) > self._onset_ratio
        else:
            onset = energy > self.threshold * 2

        hf_pass = False
        if above_noise and onset:
            fft_mag = _np.abs(_np.fft.rfft(indata.flatten()))
            n_bins = len(fft_mag)
            if n_bins > 4:
                split = max(n_bins // 4, 2)
                low_energy = float(_np.sum(fft_mag[:split] ** 2))
                high_energy = float(_np.sum(fft_mag[split:] ** 2))
                total = low_energy + high_energy
                if total > 0:
                    hf_pass = (high_energy / total) >= self._hf_ratio_min

        self._prev_energy = energy
        if energy < self.threshold * 0.5:
            self._noise_floor = (1 - self._noise_alpha) * self._noise_floor + self._noise_alpha * energy

        return (above_noise and onset and hf_pass), energy

    # ── Dispatch ─────────────────────────────────────────────
    def _is_clap(self, indata):
        if _HAS_NATIVE:
            return self._is_clap_native(indata)
        elif _np is not None:
            return self._is_clap_numpy(indata)
        else:
            return self._is_clap_pure(indata)

    # ── Main loop ────────────────────────────────────────────
    def _listen_loop(self):
        """Main audio loop — receives int16 chunks from AudioHub."""
        audio_queue = queue.Queue(maxsize=50)

        try:
            from core.audio_hub import audio_hub
            audio_hub.register(audio_queue)

            while not self._stop_event.is_set():
                # ── Paused: drain and skip ──
                if self.paused or not self.running:
                    time.sleep(0.1)
                    while not audio_queue.empty():
                        try: audio_queue.get_nowait()
                        except: break
                    continue

                # ── Get next chunk ──
                try:
                    raw = audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                now = time.time()

                # ── Debounce ──
                if now - self._last_peak_time < self._debounce:
                    # Update energy but skip detection
                    self._prev_energy = self._quick_energy(raw)
                    continue   # BUG FIX: was 'return' which killed the loop!

                # ── Detect clap ──
                if _np is not None:
                    # Numpy path: convert int16 → float32
                    samples = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
                    is_clap, energy = self._is_clap_numpy(samples)
                else:
                    # Pure Python path: process int16 directly
                    is_clap, energy = self._is_clap_int16(raw)

                if not is_clap:
                    continue

                self._last_peak_time = now

                # ── Cooldown ──
                if now - self._last_trigger_time < self.cooldown:
                    continue

                # ── Double-clap timing ──
                gap = now - self._first_clap_time

                if self._first_clap_time > 0 and self.double_clap_min < gap < self.double_clap_max:
                    self._first_clap_time = 0
                    self._last_trigger_time = now
                    print("👏👏 DOUBLE CLAP DETECTED!")
                    if self.on_clap:
                        self.on_clap()
                elif gap >= self.double_clap_max or self._first_clap_time == 0:
                    self._first_clap_time = now

        except Exception as e:
            print(f"❌ Clap Listener Error: {e}")
            self.running = False
        finally:
            try: audio_hub.unregister(audio_queue)
            except: pass

    def _quick_energy(self, raw_bytes):
        """Fast RMS energy from int16 bytes (for debounce updates)."""
        count = len(raw_bytes) // 2
        if count == 0: return 0.0
        shorts = struct.unpack(f'<{count}h', raw_bytes)
        rms = math.sqrt(sum(s*s for s in shorts) / count)
        return (rms / 32768.0) * 100.0
            
    def _is_clap_int16(self, raw_bytes):
        """Optimized for int16 audio data from AudioHub."""
        count = len(raw_bytes) // 2
        shorts = struct.unpack(f'<{count}h', raw_bytes)
        
        # RMS Energy
        sum_sq = sum(s*s for s in shorts)
        rms = math.sqrt(sum_sq / count)
        # Convert to 0-100 scale (matching float32 logic)
        energy = (rms / 32768.0) * 100.0
        
        # Above noise floor
        above_noise = energy > (self._noise_floor * self._clap_ratio) and energy > self.threshold

        # Transient onset
        if self._prev_energy > 0.01:
            onset = (energy / max(self._prev_energy, 0.01)) > self._onset_ratio
        else:
            onset = energy > self.threshold * 2

        # Update state
        self._prev_energy = energy
        if energy < self.threshold * 0.5:
            self._noise_floor = (1 - self._noise_alpha) * self._noise_floor + self._noise_alpha * energy
            
        return (above_noise and onset), energy

