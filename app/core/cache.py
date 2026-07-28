"""Simple TTL cache for hot read paths (certificate verify, stats).

In-process only — safe for single-worker and reduces DB load on multi-worker
when each worker caches independently. Prefer Redis later for shared cache.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Any, TypeVar

T = TypeVar("T")


class TtlCache:
    def __init__(self, maxsize: int = 10_000, ttl_seconds: float = 300.0) -> None:
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        expires_at = time.monotonic() + self.ttl_seconds
        with self._lock:
            self._data[key] = (expires_at, value)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


# Public certificate verify — high read traffic, immutable once issued
verify_cache = TtlCache(maxsize=50_000, ttl_seconds=600.0)

# Dashboard aggregates — short TTL
stats_cache = TtlCache(maxsize=64, ttl_seconds=60.0)
