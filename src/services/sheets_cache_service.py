"""
Dual-layer caching service for Google Sheets data with
modification-time-based invalidation.

This module provides a caching layer that reduces Google API calls by maintaining
both in-memory and on-disk caches, invalidating entries only when the underlying
Google Sheets files are modified.
"""

import json
import logging
import os
import tempfile
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.services.google_drive_service import GoogleDriveService
from src.services.google_sheets_service import GoogleSheetsService

logger = logging.getLogger(__name__)


class SheetsCacheService:
    """
    Dual-layer caching service for Google Sheets data.

    Features:
    - In-memory cache for fast access during session
    - On-disk cache for persistence across application restarts
    - Modification-time-based invalidation (only re-read if file changed)
    - Thread-safe operations with lock protection
    - LRU eviction when cache size limit is exceeded
    - Configurable cache behavior via settings

    Cache Structure:
        Memory: {(spreadsheet_id, range_name): CacheEntry}
        Disk: JSON file with versioned cache entries

    Example:
        >>> from src.services.google_sheets_service import GoogleSheetsService
        >>> from src.services.google_drive_service import GoogleDriveService
        >>> from src.config.settings import get_config
        >>> config = get_config()
        >>> sheets_service = GoogleSheetsService()
        >>> drive_service = GoogleDriveService()
        >>> cache = SheetsCacheService(
        ...     sheets_service,
        ...     drive_service,
        ...     config
        ... )
        >>> df = cache.read_sheet_cached("spreadsheet-id", "Sheet1!A1:D10")
    """

    CACHE_VERSION = "1.0"

    def __init__(
        self,
        sheets_service: GoogleSheetsService,
        drive_service: GoogleDriveService,
        config: Any,
    ):
        """
        Initialize the cache service.

        Args:
            sheets_service: Google Sheets service for reading data
            drive_service: Google Drive service for modification time checks
            config: Configuration object with cache settings
        """
        self.sheets_service = sheets_service
        self.drive_service = drive_service
        self.config = config

        # Cache settings
        self.enabled = config.enable_sheets_cache
        self.cache_file_path = Path(config.cache_file_path)
        self.max_size = config.cache_max_size
        self.auto_save = config.cache_auto_save

        # In-memory cache (LRU ordering)
        self._memory_cache: OrderedDict[Tuple[str, str], Dict[str, Any]] = OrderedDict()

        # Thread safety
        self._lock = threading.Lock()

        # Statistics
        self._stats = {
            "memory_hits": 0,
            "disk_hits": 0,
            "api_calls": 0,
            "cache_saves": 0,
            "cache_invalidations": 0,
        }

        # Load disk cache on initialization
        if self.enabled:
            self._load_from_disk()
            logger.info(
                f"SheetsCacheService initialized (enabled={self.enabled}, "
                f"max_size={self.max_size}, entries={len(self._memory_cache)})"
            )
        else:
            logger.info("SheetsCacheService initialized (caching disabled)")

    def read_sheet_cached(self, spreadsheet_id: str, range_name: str) -> pd.DataFrame:
        """
        Read sheet data with dual-layer caching and modification-based
        invalidation.

        Cache lookup flow:
        1. Check in-memory cache → Return if file unmodified
        2. Check on-disk cache → Load to memory if file unmodified
        3. Fetch from Google Sheets API → Update both cache layers

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The range to read (e.g., "Sheet1!A1:D10")

        Returns:
            DataFrame with sheet data

        Raises:
            HttpError: If API request fails
        """
        if not self.enabled:
            # Cache disabled, read directly from API
            return self.sheets_service.read_sheet(spreadsheet_id, range_name)

        cache_key = (spreadsheet_id, range_name)

        with self._lock:
            # Step 1: Check memory cache
            if cache_key in self._memory_cache:
                cached_entry = self._memory_cache[cache_key]

                # Check if file has been modified since cache time
                if self._is_cache_entry_valid(spreadsheet_id, cached_entry):
                    logger.debug(f"Memory cache hit for {spreadsheet_id}:{range_name}")
                    self._stats["memory_hits"] += 1

                    # Move to end (LRU: most recently used)
                    self._memory_cache.move_to_end(cache_key)

                    return pd.DataFrame.from_records(cached_entry["data"])
                else:
                    logger.debug(
                        f"Memory cache invalid (file modified) for "
                        f"{spreadsheet_id}:{range_name}"
                    )
                    # Remove stale entry
                    del self._memory_cache[cache_key]
                    self._stats["cache_invalidations"] += 1

            # Step 2: Memory cache miss - fetch from API
            logger.debug(
                f"Cache miss for {spreadsheet_id}:{range_name}, " f"fetching from API"
            )
            df = self.sheets_service.read_sheet(spreadsheet_id, range_name)
            self._stats["api_calls"] += 1

            # Step 3: Update cache with fresh data
            try:
                modified_time = self.drive_service.get_modification_time(spreadsheet_id)

                cache_entry = {
                    "data": df.to_dict("records"),
                    "modified_time": modified_time.isoformat(),
                    "cached_at": datetime.now().isoformat(),
                }

                # Add to memory cache (with LRU eviction if needed)
                self._add_to_memory_cache(cache_key, cache_entry)

                # Save to disk if auto-save enabled
                if self.auto_save:
                    self._save_to_disk()

            except Exception as e:
                logger.warning(f"Failed to cache data: {e}")
                # Continue without caching - return the data anyway

            return df

    def batch_read_sheets_cached(
        self, requests: List[Tuple[str, str]]
    ) -> List[pd.DataFrame]:
        """
        Read multiple sheets with caching (batched operation).

        Args:
            requests: List of (spreadsheet_id, range_name) tuples

        Returns:
            List of DataFrames in the same order as requests
        """
        results = []

        for spreadsheet_id, range_name in requests:
            df = self.read_sheet_cached(spreadsheet_id, range_name)
            results.append(df)

        # Save to disk once after batch (if auto-save enabled)
        if self.enabled and self.auto_save and requests:
            with self._lock:
                self._save_to_disk()

        return results

    def invalidate_cache(
        self, spreadsheet_id: Optional[str] = None, range_name: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            spreadsheet_id: If provided, invalidate only this spreadsheet's entries
            range_name: If provided (with spreadsheet_id), invalidate specific range
        """
        with self._lock:
            if spreadsheet_id is None:
                # Invalidate all
                count = len(self._memory_cache)
                self._memory_cache.clear()
                logger.info(f"Invalidated entire cache ({count} entries)")
                self._stats["cache_invalidations"] += count
            elif range_name is None:
                # Invalidate all ranges for this spreadsheet
                keys_to_remove = [
                    key for key in self._memory_cache if key[0] == spreadsheet_id
                ]
                for key in keys_to_remove:
                    del self._memory_cache[key]
                    self._stats["cache_invalidations"] += 1
                logger.info(
                    f"Invalidated {len(keys_to_remove)} entries for "
                    f"spreadsheet {spreadsheet_id}"
                )
            else:
                # Invalidate specific entry
                cache_key = (spreadsheet_id, range_name)
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
                    self._stats["cache_invalidations"] += 1
                    logger.info(f"Invalidated cache for {spreadsheet_id}:{range_name}")

            # Save after invalidation
            if self.auto_save:
                self._save_to_disk()

    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics including hit rates and savings
        """
        with self._lock:
            total_reads = (
                self._stats["memory_hits"]
                + self._stats["disk_hits"]
                + self._stats["api_calls"]
            )

            memory_hit_rate = (
                (self._stats["memory_hits"] / total_reads * 100)
                if total_reads > 0
                else 0
            )
            disk_hit_rate = (
                (self._stats["disk_hits"] / total_reads * 100) if total_reads > 0 else 0
            )
            total_cache_hit_rate = memory_hit_rate + disk_hit_rate

            api_calls_saved = self._stats["memory_hits"] + self._stats["disk_hits"]
            savings_percentage = (
                (api_calls_saved / total_reads * 100) if total_reads > 0 else 0
            )

            return {
                "enabled": self.enabled,
                "total_reads": total_reads,
                "memory_hits": self._stats["memory_hits"],
                "disk_hits": self._stats["disk_hits"],
                "api_calls": self._stats["api_calls"],
                "memory_hit_rate_pct": round(memory_hit_rate, 2),
                "disk_hit_rate_pct": round(disk_hit_rate, 2),
                "total_cache_hit_rate_pct": round(total_cache_hit_rate, 2),
                "api_calls_saved": api_calls_saved,
                "savings_percentage": round(savings_percentage, 2),
                "cache_invalidations": self._stats["cache_invalidations"],
                "cache_saves": self._stats["cache_saves"],
                "current_cache_size": len(self._memory_cache),
                "max_cache_size": self.max_size,
            }

    def _is_cache_entry_valid(
        self, spreadsheet_id: str, cache_entry: Dict[str, Any]
    ) -> bool:
        """
        Check if a cache entry is still valid by comparing modification times.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            cache_entry: The cached entry to validate

        Returns:
            True if cache is valid (file not modified), False otherwise
        """
        try:
            # Get current modification time from Drive API
            current_mod_time = self.drive_service.get_modification_time(spreadsheet_id)

            # Get cached modification time
            cached_mod_time_str = cache_entry.get("modified_time")
            if not cached_mod_time_str:
                logger.warning("Cache entry missing modification time")
                return False

            cached_mod_time = datetime.fromisoformat(cached_mod_time_str)

            # Compare: cache is valid if file hasn't been modified
            is_valid = current_mod_time <= cached_mod_time

            if not is_valid:
                logger.debug(
                    f"File modified: cached={cached_mod_time}, "
                    f"current={current_mod_time}"
                )

            return is_valid

        except Exception as e:
            logger.warning(f"Failed to validate cache entry: {e}")
            return False

    def _add_to_memory_cache(
        self, cache_key: Tuple[str, str], cache_entry: Dict[str, Any]
    ):
        """
        Add entry to memory cache with LRU eviction.

        Args:
            cache_key: (spreadsheet_id, range_name) tuple
            cache_entry: The cache entry to add
        """
        # Add to cache
        self._memory_cache[cache_key] = cache_entry

        # Move to end (most recently used)
        self._memory_cache.move_to_end(cache_key)

        # LRU eviction if size exceeded
        while len(self._memory_cache) > self.max_size:
            # Remove oldest entry (first item in OrderedDict)
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
            logger.debug(f"Evicted cache entry (LRU): {oldest_key}")

    def _load_from_disk(self):
        """
        Load cache from disk into memory.

        Handles missing files and corrupted data gracefully.
        """
        if not self.cache_file_path.exists():
            logger.debug(f"Cache file not found: {self.cache_file_path}")
            return

        try:
            with open(self.cache_file_path, "r") as f:
                disk_cache = json.load(f)

            # Validate version
            version = disk_cache.get("version", "unknown")
            if version != self.CACHE_VERSION:
                logger.warning(
                    f"Cache version mismatch (expected {self.CACHE_VERSION}, "
                    f"got {version}), ignoring disk cache"
                )
                return

            # Load entries into memory cache
            entries = disk_cache.get("entries", {})
            for key_str, entry in entries.items():
                # Parse key
                parts = key_str.split(":", 1)
                if len(parts) != 2:
                    logger.warning(f"Invalid cache key format: {key_str}")
                    continue

                spreadsheet_id, range_name = parts
                cache_key = (spreadsheet_id, range_name)

                # Add to memory cache (respecting max size)
                if len(self._memory_cache) < self.max_size:
                    self._memory_cache[cache_key] = entry
                else:
                    break

            logger.info(f"Loaded {len(self._memory_cache)} entries from disk cache")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cache file (corrupted JSON): {e}")
        except Exception as e:
            logger.error(f"Failed to load cache from disk: {e}")

    def _save_to_disk(self):
        """
        Save memory cache to disk using atomic write (temp file + rename).

        This ensures cache file is never corrupted even if write is interrupted.
        """
        try:
            # Ensure cache directory exists
            self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare cache data
            disk_cache = {
                "version": self.CACHE_VERSION,
                "last_updated": datetime.now().isoformat(),
                "entries": {},
            }

            # Convert memory cache to serializable format
            for (spreadsheet_id, range_name), entry in self._memory_cache.items():
                key_str = f"{spreadsheet_id}:{range_name}"
                disk_cache["entries"][key_str] = entry

            # Atomic write: write to temp file, then rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.cache_file_path.parent, suffix=".tmp"
            )

            try:
                with os.fdopen(temp_fd, "w") as f:
                    json.dump(disk_cache, f, indent=2)

                # Atomic rename (overwrites existing file)
                os.replace(temp_path, self.cache_file_path)

                self._stats["cache_saves"] += 1
                logger.debug(f"Saved {len(self._memory_cache)} entries to disk cache")

            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except (OSError, FileNotFoundError):
                    # Temp file may already be deleted, ignore
                    pass
                raise e

        except Exception as e:
            logger.error(f"Failed to save cache to disk: {e}")
