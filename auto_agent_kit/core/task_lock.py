"""
AutoAgentKit - Task Lock
========================
Distributed task locking with auto-expiry for complex multi-step workflows.

Usage:
    lock = TaskLock()
    with lock("data-pipeline", timeout=300):
        # critical section
        pass
"""

import os
import time
import json
import threading
import tempfile
from typing import Optional, Dict
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class LockInfo:
    """Information about a held lock."""
    name: str
    acquired_at: float
    expires_at: float
    owner: str
    metadata: Dict = None


class TaskLock:
    """
    Distributed task lock with auto-expiry.

    Features:
    - File-based locking (works across processes)
    - Auto-expiry (prevents deadlocks)
    - Thread-safe
    - Context manager support
    - Metadata attachment

    The lock file is stored in a configurable directory (default: system temp).
    """

    def __init__(self, lock_dir: Optional[str] = None, default_timeout: int = 300):
        self._lock_dir = Path(lock_dir or tempfile.gettempdir()) / ".auto_agent_kit_locks"
        self._lock_dir.mkdir(parents=True, exist_ok=True)
        self._default_timeout = default_timeout
        self._held_locks: Dict[str, LockInfo] = {}
        self._thread_lock = threading.Lock()

    def acquire(
        self,
        name: str,
        timeout: Optional[int] = None,
        owner: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Acquire a lock.

        Args:
            name: Lock name (e.g., "data-pipeline", "deploy")
            timeout: Lock timeout in seconds (default: 300)
            owner: Owner identifier (default: hostname)
            metadata: Optional metadata dict

        Returns:
            True if lock acquired, False if already held
        """
        timeout = timeout or self._default_timeout
        owner = owner or os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
        lock_path = self._lock_path(name)

        with self._thread_lock:
            # Check if we already hold it
            if name in self._held_locks:
                info = self._held_locks[name]
                if time.time() < info.expires_at:
                    return False  # Already held and valid
                else:
                    # Expired, release and re-acquire
                    del self._held_locks[name]

            # Check file-based lock
            if lock_path.exists():
                try:
                    data = json.loads(lock_path.read_text())
                    expires = data.get("expires_at", 0)
                    if time.time() < expires:
                        return False  # Held by another process
                except (json.JSONDecodeError, OSError):
                    pass  # Stale lock file, overwrite

            # Acquire
            now = time.time()
            info = LockInfo(
                name=name,
                acquired_at=now,
                expires_at=now + timeout,
                owner=owner,
                metadata=metadata or {},
            )

            lock_path.write_text(json.dumps({
                "name": name,
                "acquired_at": info.acquired_at,
                "expires_at": info.expires_at,
                "owner": info.owner,
                "metadata": info.metadata,
            }))

            self._held_locks[name] = info
            return True

    def release(self, name: str) -> bool:
        """
        Release a lock.

        Args:
            name: Lock name to release

        Returns:
            True if released, False if not held
        """
        lock_path = self._lock_path(name)

        with self._thread_lock:
            if name not in self._held_locks:
                return False

            del self._held_locks[name]

            if lock_path.exists():
                try:
                    lock_path.unlink()
                except OSError:
                    pass

            return True

    def is_locked(self, name: str) -> bool:
        """Check if a lock is currently held (by anyone)."""
        # Check in-process
        if name in self._held_locks:
            info = self._held_locks[name]
            if time.time() < info.expires_at:
                return True
            else:
                # Expired, clean up
                with self._thread_lock:
                    if name in self._held_locks:
                        del self._held_locks[name]

        # Check file-based
        lock_path = self._lock_path(name)
        if lock_path.exists():
            try:
                data = json.loads(lock_path.read_text())
                return time.time() < data.get("expires_at", 0)
            except (json.JSONDecodeError, OSError):
                pass

        return False

    def get_lock_info(self, name: str) -> Optional[LockInfo]:
        """Get information about a held lock."""
        lock_path = self._lock_path(name)

        if lock_path.exists():
            try:
                data = json.loads(lock_path.read_text())
                if time.time() < data.get("expires_at", 0):
                    return LockInfo(**data)
            except (json.JSONDecodeError, OSError):
                pass

        return None

    def list_locks(self) -> Dict[str, LockInfo]:
        """List all currently held locks."""
        result = {}

        # In-process locks
        for name, info in list(self._held_locks.items()):
            if time.time() < info.expires_at:
                result[name] = info
            else:
                with self._thread_lock:
                    if name in self._held_locks:
                        del self._held_locks[name]

        # File-based locks
        for lock_file in self._lock_dir.glob("*.lock"):
            name = lock_file.stem
            if name not in result:
                try:
                    data = json.loads(lock_file.read_text())
                    if time.time() < data.get("expires_at", 0):
                        result[name] = LockInfo(**data)
                except (json.JSONDecodeError, OSError):
                    pass

        return result

    def clear_expired(self) -> int:
        """Clear all expired locks. Returns count of cleared locks."""
        cleared = 0

        with self._thread_lock:
            for name in list(self._held_locks.keys()):
                if time.time() >= self._held_locks[name].expires_at:
                    del self._held_locks[name]
                    cleared += 1

        for lock_file in self._lock_dir.glob("*.lock"):
            try:
                data = json.loads(lock_file.read_text())
                if time.time() >= data.get("expires_at", 0):
                    lock_file.unlink()
                    cleared += 1
            except (json.JSONDecodeError, OSError):
                pass

        return cleared

    def _lock_path(self, name: str) -> Path:
        """Get the file path for a lock."""
        safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        return self._lock_dir / f"{safe_name}.lock"

    @contextmanager
    def __call__(self, name: str, timeout: Optional[int] = None,
                 owner: Optional[str] = None, metadata: Optional[Dict] = None):
        """Context manager support."""
        acquired = self.acquire(name, timeout, owner, metadata)
        if not acquired:
            raise LockError(f"Could not acquire lock: {name}")
        try:
            yield
        finally:
            self.release(name)


class LockError(Exception):
    """Raised when a lock cannot be acquired."""
    pass
