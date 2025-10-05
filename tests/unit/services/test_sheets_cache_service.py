"""
Unit tests for SheetsCacheService with dual-layer caching.

Tests cover:
- Memory cache hits and misses
- Disk cache persistence and loading
- Modification-time-based invalidation
- LRU eviction
- Thread safety
- Cache statistics
- Error handling
"""

import json
import threading
from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.services.sheets_cache_service import SheetsCacheService


class MockConfig:
    """Mock configuration for testing."""

    def __init__(
        self,
        enable_sheets_cache=True,
        cache_file_path=None,
        cache_max_size=100,
        cache_auto_save=True,
    ):
        self.enable_sheets_cache = enable_sheets_cache
        self.cache_file_path = cache_file_path or ".cache/test_cache.json"
        self.cache_max_size = cache_max_size
        self.cache_auto_save = cache_auto_save


@pytest.fixture
def mock_sheets_service():
    """Create mock Google Sheets service."""
    service = MagicMock()
    service.read_sheet.return_value = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    return service


@pytest.fixture
def mock_drive_service():
    """Create mock Google Drive service."""
    service = MagicMock()
    service.get_modification_time.return_value = datetime(2025, 10, 5, 10, 0, 0)
    return service


@pytest.fixture
def temp_cache_file(tmp_path):
    """Create temporary cache file path."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    return cache_dir / "test_cache.json"


@pytest.fixture
def cache_service(mock_sheets_service, mock_drive_service, temp_cache_file):
    """Create cache service with mocked dependencies."""
    config = MockConfig(cache_file_path=str(temp_cache_file))
    return SheetsCacheService(mock_sheets_service, mock_drive_service, config)


class TestCacheInitialization:
    """Test cache service initialization."""

    def test_initialization_with_caching_enabled(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test initialization with caching enabled."""
        config = MockConfig(cache_file_path=str(temp_cache_file))
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        assert service.enabled is True
        assert service.max_size == 100
        assert service.auto_save is True
        assert len(service._memory_cache) == 0

    def test_initialization_with_caching_disabled(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test initialization with caching disabled."""
        config = MockConfig(
            enable_sheets_cache=False, cache_file_path=str(temp_cache_file)
        )
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        assert service.enabled is False

    def test_initialization_loads_existing_disk_cache(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test that initialization loads existing disk cache."""
        # Create disk cache file
        disk_cache = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "entries": {
                "sheet123:Sheet1!A1:D10": {
                    "data": [{"A": 1, "B": 2}],
                    "modified_time": "2025-10-05T10:00:00+00:00",
                    "cached_at": "2025-10-05T10:00:05",
                }
            },
        }

        with open(temp_cache_file, "w") as f:
            json.dump(disk_cache, f)

        # Initialize service
        config = MockConfig(cache_file_path=str(temp_cache_file))
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        # Verify cache loaded
        assert len(service._memory_cache) == 1
        assert ("sheet123", "Sheet1!A1:D10") in service._memory_cache


class TestMemoryCache:
    """Test in-memory cache operations."""

    def test_cache_hit_returns_cached_data(self, cache_service, mock_drive_service):
        """Test that cache hit returns cached data without API call."""
        spreadsheet_id = "sheet123"
        range_name = "Sheet1!A1:D10"

        # First read (cache miss)
        df1 = cache_service.read_sheet_cached(spreadsheet_id, range_name)

        # Second read (should be cache hit)
        df2 = cache_service.read_sheet_cached(spreadsheet_id, range_name)

        # Verify data is same
        pd.testing.assert_frame_equal(df1, df2)

        # Verify sheets service called only once (first read)
        assert cache_service.sheets_service.read_sheet.call_count == 1

        # Verify cache statistics
        stats = cache_service.get_cache_statistics()
        assert stats["memory_hits"] == 1
        assert stats["api_calls"] == 1

    def test_cache_miss_fetches_from_api(self, cache_service):
        """Test that cache miss fetches data from API."""
        spreadsheet_id = "sheet123"
        range_name = "Sheet1!A1:D10"

        df = cache_service.read_sheet_cached(spreadsheet_id, range_name)

        # Verify sheets service was called
        cache_service.sheets_service.read_sheet.assert_called_once_with(
            spreadsheet_id, range_name
        )

        # Verify data returned
        assert not df.empty

        # Verify cache statistics
        stats = cache_service.get_cache_statistics()
        assert stats["api_calls"] == 1
        assert stats["memory_hits"] == 0

    def test_cache_invalidation_on_file_modification(
        self, cache_service, mock_drive_service
    ):
        """Test that cache is invalidated when file is modified."""
        spreadsheet_id = "sheet123"
        range_name = "Sheet1!A1:D10"

        # First read (cache miss)
        cache_service.read_sheet_cached(spreadsheet_id, range_name)

        # Simulate file modification
        mock_drive_service.get_modification_time.return_value = datetime(
            2025, 10, 5, 11, 0, 0
        )  # 1 hour later

        # Second read (should detect modification and fetch fresh data)
        cache_service.read_sheet_cached(spreadsheet_id, range_name)

        # Verify sheets service called twice (cache invalidated)
        assert cache_service.sheets_service.read_sheet.call_count == 2

        # Verify invalidation stat
        stats = cache_service.get_cache_statistics()
        assert stats["cache_invalidations"] == 1

    def test_lru_eviction_when_max_size_exceeded(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test LRU eviction when cache size limit is exceeded."""
        config = MockConfig(cache_file_path=str(temp_cache_file), cache_max_size=3)
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        # Add 4 entries (exceeds max size of 3)
        for i in range(4):
            service.read_sheet_cached(f"sheet{i}", "Sheet1!A1:D10")

        # Verify cache size is limited to max_size
        assert len(service._memory_cache) == 3

        # Verify oldest entry (sheet0) was evicted
        assert ("sheet0", "Sheet1!A1:D10") not in service._memory_cache

        # Verify newest entries remain
        assert ("sheet1", "Sheet1!A1:D10") in service._memory_cache
        assert ("sheet2", "Sheet1!A1:D10") in service._memory_cache
        assert ("sheet3", "Sheet1!A1:D10") in service._memory_cache


class TestDiskCache:
    """Test on-disk cache persistence."""

    def test_cache_saved_to_disk(self, cache_service, temp_cache_file):
        """Test that cache is saved to disk."""
        spreadsheet_id = "sheet123"
        range_name = "Sheet1!A1:D10"

        # Read data (should be cached)
        cache_service.read_sheet_cached(spreadsheet_id, range_name)

        # Verify cache file exists
        assert temp_cache_file.exists()

        # Verify cache file content
        with open(temp_cache_file, "r") as f:
            disk_cache = json.load(f)

        assert disk_cache["version"] == "1.0"
        assert "sheet123:Sheet1!A1:D10" in disk_cache["entries"]

    def test_cache_loaded_from_disk_on_initialization(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test that cache is loaded from disk on initialization."""
        # Create initial cache service and populate cache
        config1 = MockConfig(cache_file_path=str(temp_cache_file))
        service1 = SheetsCacheService(mock_sheets_service, mock_drive_service, config1)
        service1.read_sheet_cached("sheet123", "Sheet1!A1:D10")

        # Create new cache service (should load from disk)
        config2 = MockConfig(cache_file_path=str(temp_cache_file))
        service2 = SheetsCacheService(mock_sheets_service, mock_drive_service, config2)

        # Verify cache loaded from disk
        assert len(service2._memory_cache) == 1
        assert ("sheet123", "Sheet1!A1:D10") in service2._memory_cache

    def test_corrupted_cache_file_handled_gracefully(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test that corrupted cache file is handled gracefully."""
        # Create corrupted cache file
        with open(temp_cache_file, "w") as f:
            f.write("invalid json content {{{")

        # Initialize service (should not crash)
        config = MockConfig(cache_file_path=str(temp_cache_file))
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        # Verify service initialized with empty cache
        assert len(service._memory_cache) == 0

    def test_auto_save_disabled_does_not_save_to_disk(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test that auto-save disabled prevents disk writes."""
        config = MockConfig(cache_file_path=str(temp_cache_file), cache_auto_save=False)
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        # Read data
        service.read_sheet_cached("sheet123", "Sheet1!A1:D10")

        # Verify cache file not created
        assert not temp_cache_file.exists()


class TestCacheInvalidation:
    """Test cache invalidation methods."""

    def test_invalidate_all_cache(self, cache_service):
        """Test invalidating entire cache."""
        # Populate cache
        cache_service.read_sheet_cached("sheet1", "Sheet1!A1:D10")
        cache_service.read_sheet_cached("sheet2", "Sheet1!A1:D10")

        assert len(cache_service._memory_cache) == 2

        # Invalidate all
        cache_service.invalidate_cache()

        # Verify cache empty
        assert len(cache_service._memory_cache) == 0

    def test_invalidate_specific_spreadsheet(self, cache_service):
        """Test invalidating specific spreadsheet's entries."""
        # Populate cache
        cache_service.read_sheet_cached("sheet1", "Sheet1!A1:D10")
        cache_service.read_sheet_cached("sheet1", "Sheet2!A1:D10")
        cache_service.read_sheet_cached("sheet2", "Sheet1!A1:D10")

        assert len(cache_service._memory_cache) == 3

        # Invalidate sheet1
        cache_service.invalidate_cache(spreadsheet_id="sheet1")

        # Verify only sheet1 entries removed
        assert len(cache_service._memory_cache) == 1
        assert ("sheet2", "Sheet1!A1:D10") in cache_service._memory_cache

    def test_invalidate_specific_range(self, cache_service):
        """Test invalidating specific spreadsheet range."""
        # Populate cache
        cache_service.read_sheet_cached("sheet1", "Sheet1!A1:D10")
        cache_service.read_sheet_cached("sheet1", "Sheet2!A1:D10")

        assert len(cache_service._memory_cache) == 2

        # Invalidate specific range
        cache_service.invalidate_cache(
            spreadsheet_id="sheet1", range_name="Sheet1!A1:D10"
        )

        # Verify only specific entry removed
        assert len(cache_service._memory_cache) == 1
        assert ("sheet1", "Sheet2!A1:D10") in cache_service._memory_cache


class TestBatchOperations:
    """Test batch read operations."""

    def test_batch_read_sheets_cached(self, cache_service):
        """Test batch reading with caching."""
        requests = [
            ("sheet1", "Sheet1!A1:D10"),
            ("sheet2", "Sheet1!A1:D10"),
            ("sheet3", "Sheet1!A1:D10"),
        ]

        results = cache_service.batch_read_sheets_cached(requests)

        # Verify results returned
        assert len(results) == 3
        assert all(isinstance(df, pd.DataFrame) for df in results)

        # Verify cache populated
        assert len(cache_service._memory_cache) == 3


class TestCacheStatistics:
    """Test cache statistics tracking."""

    def test_cache_statistics_accuracy(self, cache_service):
        """Test that cache statistics are accurately tracked."""
        # API call
        cache_service.read_sheet_cached("sheet1", "Sheet1!A1:D10")

        # Memory hit
        cache_service.read_sheet_cached("sheet1", "Sheet1!A1:D10")

        # Another API call
        cache_service.read_sheet_cached("sheet2", "Sheet1!A1:D10")

        stats = cache_service.get_cache_statistics()

        assert stats["api_calls"] == 2
        assert stats["memory_hits"] == 1
        assert stats["total_reads"] == 3
        assert stats["memory_hit_rate_pct"] == pytest.approx(33.33, rel=0.01)
        assert stats["savings_percentage"] == pytest.approx(33.33, rel=0.01)

    def test_cache_statistics_with_caching_disabled(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test cache statistics when caching is disabled."""
        config = MockConfig(
            enable_sheets_cache=False, cache_file_path=str(temp_cache_file)
        )
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        # Read data (should bypass cache)
        service.read_sheet_cached("sheet1", "Sheet1!A1:D10")

        stats = service.get_cache_statistics()

        assert stats["enabled"] is False
        assert stats["api_calls"] == 0  # Stats not tracked when disabled


class TestCachingDisabled:
    """Test behavior when caching is disabled."""

    def test_disabled_cache_bypasses_caching(
        self, mock_sheets_service, mock_drive_service, temp_cache_file
    ):
        """Test that disabled cache always fetches from API."""
        config = MockConfig(
            enable_sheets_cache=False, cache_file_path=str(temp_cache_file)
        )
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        # Read twice
        service.read_sheet_cached("sheet1", "Sheet1!A1:D10")
        service.read_sheet_cached("sheet1", "Sheet1!A1:D10")

        # Verify sheets service called twice (no caching)
        assert mock_sheets_service.read_sheet.call_count == 2


class TestThreadSafety:
    """Test thread safety of cache operations."""

    def test_concurrent_cache_access(self, cache_service):
        """Test that concurrent access is thread-safe."""
        results = []
        errors = []

        def read_cache(spreadsheet_id):
            try:
                df = cache_service.read_sheet_cached(spreadsheet_id, "Sheet1!A1:D10")
                results.append(df)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=read_cache, args=(f"sheet{i % 3}",))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify results
        assert len(results) == 10


class TestErrorHandling:
    """Test error handling in cache operations."""

    def test_cache_continues_on_save_error(
        self, mock_sheets_service, mock_drive_service
    ):
        """Test that caching continues even if disk save fails."""
        # Use invalid path to trigger save error
        config = MockConfig(cache_file_path="/invalid/path/cache.json")
        service = SheetsCacheService(mock_sheets_service, mock_drive_service, config)

        # Should not raise exception
        df = service.read_sheet_cached("sheet1", "Sheet1!A1:D10")

        # Verify data returned despite save error
        assert not df.empty

    def test_cache_handles_drive_api_errors(self, cache_service, mock_drive_service):
        """Test that cache handles Drive API errors gracefully."""
        # First read (successful)
        cache_service.read_sheet_cached("sheet1", "Sheet1!A1:D10")

        # Simulate Drive API error on second read
        mock_drive_service.get_modification_time.side_effect = Exception("API error")

        # Should still return data (cache invalid, fetch fresh)
        df = cache_service.read_sheet_cached("sheet1", "Sheet1!A1:D10")
        assert not df.empty
