"""Caching logic for DSPyReasoner.

This module handles routing cache management with TTL-based expiration
and hash-based invalidation for compiled DSPy modules.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with expiration tracking."""

    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    access_count: int = 0


class RoutingCache:
    """In-memory cache for routing decisions with TTL expiration."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """Initialize routing cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries in cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._store: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        entry = self._store.get(key)
        if not entry:
            self.misses += 1
            return None

        if entry.expires_at < time.time():
            # Entry expired
            del self._store[key]
            self.misses += 1
            self.evictions += 1
            return None

        entry.access_count += 1
        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set cache value with TTL."""
        # Clean up if at max size (evict least recently used)
        if len(self._store) >= self.max_size:
            self._evict_lru()

        self._store[key] = CacheEntry(
            value=value,
            expires_at=time.time() + self.ttl_seconds,
        )

    def delete(self, key: str) -> None:
        """Delete cache entry."""
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        return {
            "size": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._store:
            return

        # Find entry with lowest access count (least recently used)
        lru_key = min(self._store.keys(), key=lambda k: self._store[k].access_count)
        del self._store[lru_key]
        self.evictions += 1


class CompiledModuleCache:
    """Cache for compiled DSPy modules with hash-based invalidation."""

    def __init__(self, cache_dir: Path | str | None = None):
        """Initialize compiled module cache.

        Args:
            cache_dir: Directory to store cache metadata
        """
        if cache_dir is None:
            cache_dir = Path(".var/cache/dspy")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "module_metadata.json"
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        """Load cache metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load cache metadata")
        return {}

    def _save_metadata(self) -> None:
        """Save cache metadata to file."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self._metadata, f, indent=2)
        except OSError:
            logger.warning("Failed to save cache metadata")

    def get_module_hash(self, module_path: Path) -> str:
        """Calculate hash of DSPy module file."""
        try:
            content = module_path.read_text()
            return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
        except OSError:
            return ""

    def is_valid(self, module_path: Path, cache_key: str) -> bool:
        """Check if cached module is still valid.

        Args:
            module_path: Path to DSPy module file
            cache_key: Cache key for the module

        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self._metadata:
            return False

        entry = self._metadata[cache_key]
        current_hash = self.get_module_hash(module_path)

        # Check if module file has changed
        if entry.get("module_hash") != current_hash:
            return False

        # Check if cache entry is expired
        expires_at = entry.get("expires_at", 0)
        return expires_at >= time.time()

    def register(self, module_path: Path, cache_key: str, ttl_hours: int = 24) -> None:
        """Register a compiled module in cache.

        Args:
            module_path: Path to DSPy module file
            cache_key: Cache key for the module
            ttl_hours: Time-to-live in hours
        """
        module_hash = self.get_module_hash(module_path)
        self._metadata[cache_key] = {
            "module_hash": module_hash,
            "module_path": str(module_path),
            "expires_at": time.time() + (ttl_hours * 3600),
            "cached_at": time.time(),
            "ttl_hours": ttl_hours,
        }
        self._save_metadata()

    def invalidate(self, cache_key: str | None = None) -> None:
        """Invalidate cache entry or all entries.

        Args:
            cache_key: Specific cache key to invalidate, or None for all
        """
        if cache_key is None:
            self._metadata.clear()
        elif cache_key in self._metadata:
            del self._metadata[cache_key]
        self._save_metadata()

    def cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._metadata.items()
            if entry.get("expires_at", 0) < current_time
        ]
        for key in expired_keys:
            del self._metadata[key]
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            self._save_metadata()


def get_cache_key(task: str, team_description: str = "", salt: str = "") -> str:
    """Generate deterministic cache key for routing decisions."""
    content = f"{task}:{team_description}:{salt}"
    # MD5 used for cache key generation, not security
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
