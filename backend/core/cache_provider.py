"""
Provider Pattern cache implementation for leaderboard caching.

This module defines an abstract interface for leaderboard caching, allowing
easy swapping between in-memory (DictLeaderboardCache) and Redis implementations.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class LeaderboardCache(ABC):
    """Abstract base class for leaderboard caching implementations."""

    @abstractmethod
    async def get_top_10(self, month_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached top 10 clips for a month.

        Args:
            month_key: Month in YYYY-MM format

        Returns:
            List of top 10 clips or None if not cached
        """
        pass

    @abstractmethod
    async def set_top_10(self, month_key: str, clips: List[Dict[str, Any]]) -> None:
        """Cache the top 10 clips for a month.

        Args:
            month_key: Month in YYYY-MM format
            clips: List of top 10 clip dictionaries
        """
        pass

    @abstractmethod
    async def get_clip_rank(self, clip_id: int) -> Optional[int]:
        """Get cached rank for a clip.

        Args:
            clip_id: Clip ID

        Returns:
            Rank (1-10) or None if not in cache
        """
        pass

    @abstractmethod
    async def set_clip_rank(self, clip_id: int, rank: int) -> None:
        """Cache the rank for a clip.

        Args:
            clip_id: Clip ID
            rank: Rank (1-10)
        """
        pass

    @abstractmethod
    async def invalidate(self, month_key: str) -> None:
        """Invalidate cache for a month.

        Args:
            month_key: Month in YYYY-MM format to invalidate
        """
        pass


class DictLeaderboardCache(LeaderboardCache):
    """In-memory dictionary-based leaderboard cache implementation.

    Thread-safe for basic operations (Python dict operations are atomic).
    Suitable for single-process deployments.
    """

    def __init__(self) -> None:
        """Initialize cache with empty dictionaries."""
        # Cache format: {month_key: [{rank, clip_id, score, ...}, ...]}
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

        # Cache format: {clip_id: rank}
        self._clip_ranks: Dict[int, int] = {}

        logger.info("DictLeaderboardCache initialized")

    async def get_top_10(self, month_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached top 10 for a month."""
        cached = self._cache.get(month_key)
        if cached:
            logger.debug(f"Cache HIT: top 10 for {month_key}")
            return cached
        logger.debug(f"Cache MISS: top 10 for {month_key}")
        return None

    async def set_top_10(self, month_key: str, clips: List[Dict[str, Any]]) -> None:
        """Cache top 10 for a month."""
        self._cache[month_key] = clips

        # Also update clip ranks
        for clip in clips:
            self._clip_ranks[clip["clip_id"]] = clip["rank"]

        logger.debug(f"Cached top 10 for {month_key}: {len(clips)} clips")

    async def get_clip_rank(self, clip_id: int) -> Optional[int]:
        """Get cached rank for a clip."""
        rank = self._clip_ranks.get(clip_id)
        if rank is not None:
            logger.debug(f"Cache HIT: rank for clip {clip_id} = {rank}")
            return rank
        logger.debug(f"Cache MISS: rank for clip {clip_id}")
        return None

    async def set_clip_rank(self, clip_id: int, rank: int) -> None:
        """Cache rank for a clip."""
        self._clip_ranks[clip_id] = rank
        logger.debug(f"Cached rank for clip {clip_id} = {rank}")

    async def invalidate(self, month_key: str) -> None:
        """Invalidate cache for a month."""
        if month_key in self._cache:
            # Get all clip IDs in this month
            clips = self._cache[month_key]
            for clip in clips:
                clip_id = clip["clip_id"]
                if clip_id in self._clip_ranks:
                    del self._clip_ranks[clip_id]

            del self._cache[month_key]
            logger.info(f"Invalidated cache for {month_key}")


# Global cache instance
_cache_instance: Optional[LeaderboardCache] = None


def get_cache_provider() -> LeaderboardCache:
    """Get or create the global cache provider instance.

    Returns:
        Singleton LeaderboardCache instance
    """
    global _cache_instance

    if _cache_instance is None:
        # Currently using in-memory cache
        # In the future, this can be easily swapped to RedisLeaderboardCache
        _cache_instance = DictLeaderboardCache()
        logger.info("Initialized global cache provider")

    return _cache_instance


async def reset_cache_provider() -> None:
    """Reset the cache provider (useful for testing)."""
    global _cache_instance
    _cache_instance = None
    logger.info("Cache provider reset")
