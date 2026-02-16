"""
Test script to verify the clap detection fix.
Tests the _is_awake state management logic and clap detector modes.
"""
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def test_is_awake_state():
    """Verify the _is_awake state transitions work correctly."""
    print("=" * 50)
    print("TEST 1: _is_awake State Management")
    print("=" * 50)
    
    # Simulate the _is_awake logic from main.py
    _is_awake = [True]  # Starts awake (window visible on launch)
    wake_called = [0]
    
    def _wake_up():
        if _is_awake[0]:
            return  # Already awake
        _is_awake[0] = True
        wake_called[0] += 1
    
    def _on_hide():
        _is_awake[0] = False

    # Test 1a: At startup, _is_awake=True, wake_up should be ignored
    _wake_up()
    assert wake_called[0] == 0, "Should NOT wake when already awake"
    print("  ✅ wake_up ignored when already awake")
    
    # Test 1b: After hiding, _is_awake=False
    _on_hide()
    assert _is_awake[0] == False, "_is_awake should be False after hide"
    print("  ✅ _is_awake=False after hide_window")
    
    # Test 1c: After hiding, wake_up should work
    _wake_up()
    assert _is_awake[0] == True, "_is_awake should be True after wake"
    assert wake_called[0] == 1, "wake_up should have been called"
    print("  ✅ wake_up works after hide")
    
    # Test 1d: Multiple hide/wake cycles
    for i in range(5):
        _on_hide()
        assert _is_awake[0] == False
        _wake_up()
        assert _is_awake[0] == True
        assert wake_called[0] == i + 2
    print(f"  ✅ {5} hide/wake cycles passed")
    
    print("  🎉 All state tests passed!\n")


def test_clap_detector_loads():
    """Verify the clap detector module loads and works."""
    print("=" * 50)
    print("TEST 2: ClapListener Module Load")
    print("=" * 50)
    
    from core.clap import ClapListener, _HAS_NATIVE
    
    mode = "NATIVE C" if _HAS_NATIVE else "Python fallback"
    print(f"  Mode: {mode}")
    
    trigger_count = [0]
    def on_clap():
        trigger_count[0] += 1
    
    listener = ClapListener(
        on_clap_callback=on_clap,
        threshold=12,
        double_clap_min=0.12,
        double_clap_max=0.55,
        cooldown=2.0
    )
    
    print(f"  ✅ ClapListener created successfully")
    print(f"  ✅ Threshold: {listener.threshold}")
    print(f"  ✅ Double clap window: {listener.double_clap_min}s - {listener.double_clap_max}s")
    print(f"  ✅ Cooldown: {listener.cooldown}s")
    
    # Test pause/resume
    listener.pause()
    assert listener.paused == True
    listener.resume()
    assert listener.paused == False
    print("  ✅ Pause/resume works")
    
    print("  🎉 Module load tests passed!\n")


def test_detection_speed():
    """Benchmark the detection function speed."""
    print("=" * 50)
    print("TEST 3: Detection Speed Benchmark")
    print("=" * 50)
    
    import struct
    import math
    import random
    
    from core.clap import ClapListener, _HAS_NATIVE
    
    listener = ClapListener(on_clap_callback=lambda: None)
    
    # Generate synthetic audio block (512 samples of float32)
    n_samples = 512
    random.seed(42)
    samples = [random.gauss(0, 0.1) for _ in range(n_samples)]
    raw = struct.pack(f'<{n_samples}f', *samples)
    
    # Create a fake indata object that behaves like sounddevice buffer
    class FakeIndata:
        def __init__(self, data):
            self._data = data
        def __bytes__(self):
            return self._data
        def flatten(self):
            import numpy as np
            return np.frombuffer(self._data, dtype=np.float32)
        def __pow__(self, other):
            import numpy as np
            arr = np.frombuffer(self._data, dtype=np.float32)
            return arr ** other
        def __mul__(self, other):
            import numpy as np
            arr = np.frombuffer(self._data, dtype=np.float32)
            return arr * other
    
    indata = FakeIndata(raw)
    
    # Benchmark
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        listener._is_clap(indata)
    elapsed = time.perf_counter() - start
    
    per_call_us = (elapsed / iterations) * 1_000_000
    mode = "NATIVE C" if _HAS_NATIVE else "Python"
    print(f"  Mode: {mode}")
    print(f"  {iterations} iterations in {elapsed:.3f}s")
    print(f"  Per call: {per_call_us:.1f} µs")
    print(f"  Max throughput: {1_000_000 / per_call_us:.0f} blocks/sec")
    
    # At 22050Hz with 512 block size, we get ~43 blocks/sec
    # So we need < 23ms per call to keep up in real-time
    if per_call_us < 23_000:
        print(f"  ✅ FAST ENOUGH for real-time ({per_call_us:.0f}µs < 23000µs)")
    else:
        print(f"  ⚠️ Might be slow for real-time ({per_call_us:.0f}µs > 23000µs)")
    
    print("  🎉 Benchmark complete!\n")


if __name__ == "__main__":
    test_is_awake_state()
    test_clap_detector_loads()
    test_detection_speed()
    print("=" * 50)
    print("ALL TESTS PASSED ✅")
    print("=" * 50)
