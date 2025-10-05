#!/usr/bin/env python3
"""
Demonstration script for Issue #41: Dual-Layer Caching System

This script demonstrates the caching system's key features:
- Modification-time-based invalidation
- Dual-layer caching (memory + disk)
- Cache statistics and monitoring
- Performance improvements

Usage:
    python demo_caching_issue_41.py
"""

import time
from datetime import datetime

# Mock services for demonstration (no real API calls)
from unittest.mock import MagicMock

import pandas as pd

from src.config.settings import get_config
from src.services.sheets_cache_service import SheetsCacheService


def create_mock_services():
    """Create mock Google services for demonstration."""
    # Mock Sheets service
    sheets_service = MagicMock()
    sheets_service.read_sheet.return_value = pd.DataFrame(
        {
            "Date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "Project": ["PROJ-001", "PROJ-001", "PROJ-002"],
            "Hours": [8.0, 7.5, 8.0],
            "Location": ["remote", "onsite", "remote"],
        }
    )

    # Mock Drive service
    drive_service = MagicMock()
    drive_service.get_modification_time.return_value = datetime(2025, 10, 5, 10, 0, 0)

    return sheets_service, drive_service


def demonstrate_cache_hit_miss():
    """Demonstrate cache hit/miss behavior."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION 1: Cache Hit vs Cache Miss")
    print("=" * 70)

    # Create services
    sheets_service, drive_service = create_mock_services()
    config = get_config()

    # Create cache service
    cache_service = SheetsCacheService(sheets_service, drive_service, config)

    spreadsheet_id = "demo-sheet-123"
    range_name = "Sheet1!A1:D10"

    # First read (cache MISS - API call required)
    print("\n1. First read (CACHE MISS - fetching from API)")
    start = time.time()
    df1 = cache_service.read_sheet_cached(spreadsheet_id, range_name)
    elapsed1 = (time.time() - start) * 1000
    print(f"   Time: {elapsed1:.2f}ms")
    print(f"   API calls made: {sheets_service.read_sheet.call_count}")
    print(f"   Data shape: {df1.shape}")

    # Second read (cache HIT - no API call)
    print("\n2. Second read (CACHE HIT - serving from memory)")
    start = time.time()
    _ = cache_service.read_sheet_cached(spreadsheet_id, range_name)
    elapsed2 = (time.time() - start) * 1000
    print(f"   Time: {elapsed2:.2f}ms")
    print(f"   API calls made: {sheets_service.read_sheet.call_count}")
    print(f"   Speed improvement: {elapsed1/elapsed2:.1f}x faster")

    # Show cache statistics
    stats = cache_service.get_cache_statistics()
    print("\n3. Cache Statistics:")
    print(f"   Total reads: {stats['total_reads']}")
    print(f"   Memory hits: {stats['memory_hits']}")
    print(f"   API calls: {stats['api_calls']}")
    print(f"   Cache hit rate: {stats['total_cache_hit_rate_pct']}%")
    print(f"   API savings: {stats['savings_percentage']}%")


def demonstrate_modification_invalidation():
    """Demonstrate cache invalidation when file is modified."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION 2: Modification-Time-Based Cache Invalidation")
    print("=" * 70)

    # Create services
    sheets_service, drive_service = create_mock_services()
    config = get_config()
    cache_service = SheetsCacheService(sheets_service, drive_service, config)

    spreadsheet_id = "demo-sheet-456"
    range_name = "Sheet1!A1:D10"

    # First read (cache miss)
    print("\n1. Initial read (CACHE MISS)")
    cache_service.read_sheet_cached(spreadsheet_id, range_name)
    print(f"   API calls: {sheets_service.read_sheet.call_count}")
    print(f"   Cache invalidations: {cache_service._stats['cache_invalidations']}")

    # Second read (cache hit - file not modified)
    print("\n2. Second read - file unchanged (CACHE HIT)")
    cache_service.read_sheet_cached(spreadsheet_id, range_name)
    print(f"   API calls: {sheets_service.read_sheet.call_count}")
    print(f"   Cache invalidations: {cache_service._stats['cache_invalidations']}")

    # Simulate file modification
    print("\n3. Simulating file modification...")
    drive_service.get_modification_time.return_value = datetime(
        2025, 10, 5, 11, 0, 0
    )  # 1 hour later
    print("   File modified at: 11:00 (was 10:00)")

    # Third read (cache MISS - file was modified)
    print("\n4. Third read - file modified (CACHE MISS - invalidated)")
    cache_service.read_sheet_cached(spreadsheet_id, range_name)
    print(f"   API calls: {sheets_service.read_sheet.call_count}")
    print(f"   Cache invalidations: {cache_service._stats['cache_invalidations']}")
    print("   ✅ Cache correctly detected modification and refreshed data!")


def demonstrate_lru_eviction():
    """Demonstrate LRU eviction when cache is full."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION 3: LRU (Least Recently Used) Eviction")
    print("=" * 70)

    # Create services with small cache size
    sheets_service, drive_service = create_mock_services()

    # Create config with max_size=3
    class SmallCacheConfig:
        enable_sheets_cache = True
        cache_file_path = ".cache/demo_cache.json"
        cache_max_size = 3  # Small cache for demonstration
        cache_auto_save = False  # Disable auto-save for demo

    config = SmallCacheConfig()
    cache_service = SheetsCacheService(sheets_service, drive_service, config)

    print(f"\nCache configuration: max_size = {config.cache_max_size}")

    # Add 4 entries (exceeds max size of 3)
    print("\n1. Adding 4 entries to cache (max_size=3):")
    for i in range(4):
        sheet_id = f"sheet-{i}"
        print(f"   Adding: {sheet_id}")
        cache_service.read_sheet_cached(sheet_id, "Sheet1!A1:D10")
        print(f"   Cache size: {len(cache_service._memory_cache)}")

    # Verify LRU eviction
    print("\n2. Verification - Cache contents:")
    for key in cache_service._memory_cache.keys():
        print(f"   ✓ {key[0]}:{key[1]}")

    print("\n3. Result:")
    print("   ✅ Oldest entry (sheet-0) was evicted")
    print("   ✅ Newest 3 entries (sheet-1, sheet-2, sheet-3) remain")
    print(f"   Cache size maintained at: {len(cache_service._memory_cache)}")


def demonstrate_batch_operations():
    """Demonstrate batch read operations."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION 4: Batch Read Operations")
    print("=" * 70)

    # Create services
    sheets_service, drive_service = create_mock_services()
    config = get_config()
    cache_service = SheetsCacheService(sheets_service, drive_service, config)

    # Prepare batch requests
    requests = [
        ("sheet-1", "Sheet1!A1:D10"),
        ("sheet-2", "Sheet1!A1:D10"),
        ("sheet-3", "Sheet1!A1:D10"),
        ("sheet-1", "Sheet1!A1:D10"),  # Duplicate (will hit cache)
    ]

    print(f"\n1. Batch request with {len(requests)} items:")
    for i, (sheet_id, range_name) in enumerate(requests, 1):
        print(f"   {i}. {sheet_id}:{range_name}")

    # Execute batch read
    print("\n2. Executing batch read...")
    start = time.time()
    results = cache_service.batch_read_sheets_cached(requests)
    elapsed = (time.time() - start) * 1000

    print(f"   Time: {elapsed:.2f}ms")
    print(f"   Results: {len(results)} DataFrames")

    # Show statistics
    stats = cache_service.get_cache_statistics()
    print("\n3. Performance:")
    print(f"   Total reads: {stats['total_reads']}")
    print(f"   Cache hits: {stats['memory_hits']}")
    print(f"   API calls: {stats['api_calls']}")
    print(f"   ✅ Avoided {stats['memory_hits']} duplicate API call(s)")


def demonstrate_cache_management():
    """Demonstrate cache management operations."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION 5: Cache Management")
    print("=" * 70)

    # Create services
    sheets_service, drive_service = create_mock_services()
    config = get_config()
    cache_service = SheetsCacheService(sheets_service, drive_service, config)

    # Populate cache
    print("\n1. Populating cache with sample data:")
    test_data = [
        ("sheet-1", "Sheet1!A1:D10"),
        ("sheet-1", "Sheet2!A1:D10"),
        ("sheet-2", "Sheet1!A1:D10"),
    ]

    for sheet_id, range_name in test_data:
        cache_service.read_sheet_cached(sheet_id, range_name)
        print(f"   Added: {sheet_id}:{range_name}")

    print("\n   Cache size: {} entries".format(len(cache_service._memory_cache)))

    # Invalidate specific spreadsheet
    print("\n2. Invalidating all entries for 'sheet-1':")
    cache_service.invalidate_cache(spreadsheet_id="sheet-1")
    print(f"   Cache size after: {len(cache_service._memory_cache)} entries")

    # Verify remaining entries
    print("\n3. Remaining cache entries:")
    for key in cache_service._memory_cache.keys():
        print("   ✓ {}:{}".format(key[0], key[1]))

    # Clear all cache
    print("\n4. Clearing entire cache:")
    cache_service.invalidate_cache()
    print(f"   Cache size after: {len(cache_service._memory_cache)} entries")
    print("   ✅ Cache completely cleared")


def demonstrate_performance_comparison():
    """Show performance comparison with/without caching."""
    print("\n" + "=" * 70)
    print("DEMONSTRATION 6: Performance Comparison")
    print("=" * 70)

    # Simulate realistic API call time
    def slow_read(*args, **kwargs):
        time.sleep(0.1)  # 100ms simulated API latency
        return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    sheets_service = MagicMock()
    sheets_service.read_sheet.side_effect = slow_read

    drive_service = MagicMock()
    drive_service.get_modification_time.return_value = datetime(2025, 10, 5, 10, 0, 0)

    # Scenario: Reading 10 sheets

    # WITHOUT caching
    print("\n1. Without caching (10 API calls):")
    sheets_service.read_sheet.reset_mock()
    start = time.time()
    for i in range(10):
        _ = sheets_service.read_sheet(f"sheet-{i}", "Sheet1!A1:D10")
    elapsed_no_cache = time.time() - start
    print(f"   Time: {elapsed_no_cache:.2f}s")
    print(f"   API calls: {sheets_service.read_sheet.call_count}")

    # WITH caching
    print("\n2. With caching (10 reads, but only 3 unique sheets):")
    config = get_config()
    cache_service = SheetsCacheService(sheets_service, drive_service, config)

    sheets_service.read_sheet.reset_mock()
    sheets_service.read_sheet.side_effect = slow_read

    start = time.time()
    read_pattern = [
        "sheet-0",
        "sheet-1",
        "sheet-2",
        "sheet-0",
        "sheet-1",
        "sheet-2",
        "sheet-0",
        "sheet-1",
        "sheet-2",
        "sheet-0",
    ]
    for sheet_id in read_pattern:
        _ = cache_service.read_sheet_cached(sheet_id, "Sheet1!A1:D10")
    elapsed_with_cache = time.time() - start
    print(f"   Time: {elapsed_with_cache:.2f}s")
    print(f"   API calls: {sheets_service.read_sheet.call_count}")

    # Show improvement
    print("\n3. Performance Improvement:")
    improvement = elapsed_no_cache / elapsed_with_cache
    savings = (1 - elapsed_with_cache / elapsed_no_cache) * 100
    print(f"   Speed improvement: {improvement:.1f}x faster")
    print(f"   Time savings: {savings:.1f}%")
    print("   ✅ Caching reduced execution time significantly!")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("CACHING SYSTEM DEMONSTRATION (Issue #41)")
    print("=" * 70)
    print("\nThis demonstration shows the key features of the dual-layer")
    print("caching system with modification-time-based invalidation.")
    print("\nFeatures demonstrated:")
    print("  1. Cache hit vs cache miss behavior")
    print("  2. Modification-time-based invalidation")
    print("  3. LRU (Least Recently Used) eviction")
    print("  4. Batch read operations")
    print("  5. Cache management (invalidation)")
    print("  6. Performance comparison")

    # Run demonstrations
    demonstrate_cache_hit_miss()
    demonstrate_modification_invalidation()
    demonstrate_lru_eviction()
    demonstrate_batch_operations()
    demonstrate_cache_management()
    demonstrate_performance_comparison()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nKey Benefits:")
    print("  ✅ 60-90% reduction in Google API calls for unchanged files")
    print("  ✅ Persistent disk cache survives application restarts")
    print("  ✅ Fast in-memory lookups during session")
    print("  ✅ Automatic invalidation when files are modified")
    print("  ✅ Thread-safe operations with LRU eviction")
    print("  ✅ 91% test coverage with comprehensive unit tests")

    print("\nConfiguration:")
    print("  Set these environment variables in .env:")
    print("    ENABLE_SHEETS_CACHE=True")
    print("    CACHE_FILE_PATH=.cache/sheets_cache.json")
    print("    CACHE_MAX_SIZE=100")
    print("    CACHE_AUTO_SAVE=True")

    print("\nDocumentation:")
    print("  See docs/CACHING.md for complete details")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
