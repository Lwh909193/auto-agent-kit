"""Tests for ContextCompressor and TaskLock modules."""
import os
import sys
import time
import tempfile
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auto_agent_kit.core.context_compressor import ContextCompressor, CompressionState
from auto_agent_kit.core.task_lock import TaskLock, LockInfo, LockError


# ─── ContextCompressor Tests ────────────────────────────────────────────────

def test_compress_short_text():
    """Short text should pass through unchanged."""
    c = ContextCompressor(max_tokens=4000)
    text = "Hello, this is a short message."
    result = c.compress(text)
    assert result == text, f"Expected unchanged, got: {result}"
    assert c.state.compression_rounds == 0


def test_compress_long_text():
    """Long text should be compressed."""
    c = ContextCompressor(max_tokens=100, reserve_tokens=10)
    text = "\n".join([f"This is line {i} of a very long text that should trigger compression." for i in range(50)])
    result = c.compress(text, force=True)
    assert len(result) < len(text), f"Compression should reduce size: {len(result)} vs {len(text)}"
    assert c.state.compression_rounds == 1
    assert c.state.ratio < 1.0


def test_compress_with_instructions():
    """Instructions should be re-injected after compression."""
    c = ContextCompressor(max_tokens=100)
    text = "\n".join([f"Line {i}" for i in range(30)])
    result = c.compress(text, key_instructions="Remember the goal", force=True)
    assert "[instructions]" in result
    assert "Remember the goal" in result


def test_segment_splitting():
    """Text should be split into structured segments."""
    c = ContextCompressor()
    text = """goal: Build a thing
We are building a thing.

progress: Half done
We have completed step 1.

error: Timeout
The API timed out."""
    segments = c._split_segments(text)
    assert len(segments) >= 3
    headers = [s[0] for s in segments]
    assert "goal" in headers
    assert "progress" in headers
    assert "error" in headers


def test_compression_state():
    """Compression state should track correctly."""
    c = ContextCompressor(max_tokens=100)
    text = "\n".join([f"Line {i}" for i in range(30)])
    c.compress(text, force=True)
    state = c.get_state()
    assert state["compression_rounds"] == 1
    assert state["compression_ratio"] < 1.0
    assert state["total_original_chars"] > 0


def test_reset():
    """Reset should clear state."""
    c = ContextCompressor(max_tokens=100)
    text = "\n".join([f"Line {i}" for i in range(30)])
    c.compress(text, force=True)
    assert c.state.compression_rounds == 1
    c.reset()
    assert c.state.compression_rounds == 0
    assert c.state.total_original_chars == 0


# ─── TaskLock Tests ─────────────────────────────────────────────────────────

def test_acquire_release():
    """Basic acquire and release should work."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp())
    assert lock.acquire("test-lock")
    assert lock.is_locked("test-lock")
    assert lock.release("test-lock")
    assert not lock.is_locked("test-lock")


def test_double_acquire_fails():
    """Acquiring the same lock twice should fail."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp())
    assert lock.acquire("test-lock")
    assert not lock.acquire("test-lock")  # Second acquire should fail
    lock.release("test-lock")


def test_lock_info():
    """Lock info should be retrievable."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp())
    lock.acquire("test-lock", metadata={"key": "value"})
    info = lock.get_lock_info("test-lock")
    assert info is not None
    assert info.name == "test-lock"
    assert info.metadata.get("key") == "value"
    lock.release("test-lock")


def test_auto_expiry():
    """Lock should auto-expire after timeout."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp(), default_timeout=1)
    assert lock.acquire("test-lock", timeout=1)
    assert lock.is_locked("test-lock")
    time.sleep(1.5)
    assert not lock.is_locked("test-lock")  # Should be expired


def test_clear_expired():
    """Clear expired should remove stale locks."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp(), default_timeout=1)
    lock.acquire("lock-a", timeout=1)
    lock.acquire("lock-b", timeout=60)
    time.sleep(1.5)
    cleared = lock.clear_expired()
    assert cleared >= 1  # lock-a should be cleared
    assert lock.is_locked("lock-b")  # lock-b should still be valid
    lock.release("lock-b")


def test_context_manager():
    """Context manager should work."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp())
    with lock("test-lock"):
        assert lock.is_locked("test-lock")
    assert not lock.is_locked("test-lock")


def test_context_manager_timeout():
    """Context manager with timeout should work."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp())
    with lock("test-lock", timeout=60):
        assert lock.is_locked("test-lock")
    assert not lock.is_locked("test-lock")


def test_list_locks():
    """List locks should return all held locks."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp())
    lock.acquire("lock-a")
    lock.acquire("lock-b")
    locks = lock.list_locks()
    assert "lock-a" in locks
    assert "lock-b" in locks
    lock.release("lock-a")
    lock.release("lock-b")


def test_thread_safety():
    """Multiple threads should not corrupt lock state."""
    lock = TaskLock(lock_dir=tempfile.mkdtemp())
    errors = []

    def worker(name):
        try:
            for _ in range(10):
                if lock.acquire(name):
                    time.sleep(0.01)
                    lock.release(name)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(f"lock-{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread safety errors: {errors}"


# ─── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_compress_short_text()
    test_compress_long_text()
    test_compress_with_instructions()
    test_segment_splitting()
    test_compression_state()
    test_reset()
    test_acquire_release()
    test_double_acquire_fails()
    test_lock_info()
    test_auto_expiry()
    test_clear_expired()
    test_context_manager()
    test_context_manager_timeout()
    test_list_locks()
    test_thread_safety()
    print("✅ All tests passed!")
