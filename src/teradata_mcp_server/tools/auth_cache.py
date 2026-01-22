"""
Secure authentication session cache with expiration and thread safety.
"""

import threading
import time
from dataclasses import dataclass
from typing import NamedTuple, Optional


@dataclass
class AuthCacheEntry:
    """Authentication cache entry with expiration."""
    principal: str
    auth_hash: str
    expires_at: float
    created_at: float


class SecureAuthCache:
    """Thread-safe authentication cache with TTL expiration."""

    def __init__(self, ttl_seconds: int = 300):  # 5-minute default
        self._cache: dict[str, AuthCacheEntry] = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds

    def get(self, session_id: str, auth_hash: str) -> str | None:
        """
        Get cached principal if session_id + auth_hash match and not expired.
        Returns None if not found, hash mismatch, or expired.
        """
        with self._lock:
            entry = self._cache.get(session_id)
            if not entry:
                return None

            current_time = time.time()

            # Check expiration
            if current_time >= entry.expires_at:
                del self._cache[session_id]
                return None

            # Check auth hash match (prevents session hijacking)
            if entry.auth_hash != auth_hash:
                return None

            return entry.principal

    def set(self, session_id: str, principal: str, auth_hash: str):
        """Cache authenticated principal for session with auth hash."""
        current_time = time.time()
        with self._lock:
            self._cache[session_id] = AuthCacheEntry(
                principal=principal,
                auth_hash=auth_hash,
                expires_at=current_time + self._ttl,
                created_at=current_time
            )


    def invalidate(self, session_id: str):
        """Remove cached entry for session."""
        with self._lock:
            self._cache.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed."""
        current_time = time.time()
        expired_sessions = []

        with self._lock:
            for session_id, entry in self._cache.items():
                if current_time >= entry.expires_at:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self._cache[session_id]

        return len(expired_sessions)

    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Return current cache size."""
        with self._lock:
            return len(self._cache)

    def get_stats(self) -> dict:
        """Get cache statistics."""
        current_time = time.time()
        active_count = 0
        expired_count = 0

        with self._lock:
            for entry in self._cache.values():
                if current_time < entry.expires_at:
                    active_count += 1
                else:
                    expired_count += 1

        return {
            "total_entries": len(self._cache),
            "active_entries": active_count,
            "expired_entries": expired_count,
            "ttl_seconds": self._ttl
        }
