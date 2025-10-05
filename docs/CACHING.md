# Caching System Guide

## Overview

The billing system implements a **dual-layer caching system** with **modification-time-based invalidation** to dramatically reduce Google API calls while ensuring data freshness.

### Key Benefits

- **60-90% reduction** in Google API calls for unchanged files
- **Persistent across restarts**: On-disk cache survives application restarts
- **Fast session performance**: In-memory cache provides instant access
- **Always fresh**: Automatically detects and re-reads modified files
- **Transparent integration**: Works seamlessly with existing code

## Architecture

### Dual-Layer Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (TimesheetReader, ProjectTermsReader)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               SheetsCacheService                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Layer 1: In-Memory Cache (OrderedDict with LRU)       │ │
│  │ - Fast lookups (O(1) access time)                     │ │
│  │ - Session-scoped (cleared on restart)                 │ │
│  │ - LRU eviction when size limit exceeded               │ │
│  └────────────────────────────────────────────────────────┘ │
│                         │                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Layer 2: On-Disk Cache (JSON file)                    │ │
│  │ - Persistent across restarts                          │ │
│  │ - Atomic writes prevent corruption                    │ │
│  │ - Loaded into memory on startup                       │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          GoogleDriveService.get_modification_time()          │
│  - Fetches file's modifiedTime from Drive API               │
│  - Compares with cached modification time                   │
│  - Invalidates cache if file changed                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              GoogleSheetsService.read_sheet()                │
│  - Only called when cache miss or file modified             │
│  - Result cached for future requests                        │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

### Cache Lookup Flow

1. **Check in-memory cache**
   - Cache key: `(spreadsheet_id, range_name)`
   - If found → Compare file's current modification time with cached time
   - If modification times match → Return cached data (cache hit)
   - If modification times differ → Invalidate cache entry

2. **On cache miss**
   - Fetch fresh data from Google Sheets API
   - Get file's modification time from Drive API
   - Store in both memory and disk caches
   - Return data to caller

3. **LRU eviction** (when cache full)
   - Oldest (least recently used) entry is removed
   - Makes room for new entry
   - Configurable size limit (default: 100 entries)

### Modification-Time-Based Invalidation

```python
# Cached entry structure
{
    "data": [...],  # DataFrame as list of records
    "modified_time": "2025-10-05T10:00:00+00:00",  # RFC 3339 timestamp
    "cached_at": "2025-10-05T10:00:05"  # When cached
}

# Validation check
current_mod_time = drive_service.get_modification_time(spreadsheet_id)
cached_mod_time = datetime.fromisoformat(entry["modified_time"])

if current_mod_time > cached_mod_time:
    # File was modified, invalidate cache
    del cache[key]
    fetch_fresh_data()
else:
    # File unchanged, use cached data
    return cached_data
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Enable/disable caching (default: True)
ENABLE_SHEETS_CACHE=True

# Cache file location (default: .cache/sheets_cache.json)
CACHE_FILE_PATH=.cache/sheets_cache.json

# Maximum cache entries (default: 100)
CACHE_MAX_SIZE=100

# Auto-save to disk after each update (default: True)
CACHE_AUTO_SAVE=True
```

### Programmatic Configuration

```python
from src.config.settings import get_config

config = get_config()

# Check cache status
print(f"Cache enabled: {config.enable_sheets_cache}")
print(f"Cache file: {config.cache_file_path}")
print(f"Max size: {config.cache_max_size}")
```

## Usage

### With TimesheetReader

```python
from src.services.google_sheets_service import GoogleSheetsService
from src.services.google_drive_service import GoogleDriveService
from src.services.sheets_cache_service import SheetsCacheService
from src.readers.timesheet_reader import TimesheetReader
from src.config.settings import get_config

# Initialize services
config = get_config()
sheets_service = GoogleSheetsService()
drive_service = GoogleDriveService()

# Create cache service
cache_service = SheetsCacheService(
    sheets_service,
    drive_service,
    config
)

# Create reader with cache
reader = TimesheetReader(
    sheets_service=sheets_service,
    cache_service=cache_service  # Optional, backward compatible
)

# Read timesheets (will use cache when appropriate)
entries = reader.read_timesheet("spreadsheet-id-123")
```

### With ProjectTermsReader

```python
from src.readers.project_terms_reader import ProjectTermsReader

# Create reader with cache
reader = ProjectTermsReader(
    sheets_service=sheets_service,
    spreadsheet_id="terms-spreadsheet-id",
    cache_service=cache_service  # Optional
)

# Read project terms (will use cache when appropriate)
terms = reader.get_project_terms("John Doe", "PROJ-001")
```

### Without Cache (Backward Compatible)

```python
# Cache is optional, readers work without it
reader = TimesheetReader(sheets_service=sheets_service)

# Works exactly as before (no caching)
entries = reader.read_timesheet("spreadsheet-id-123")
```

## Cache Management

### View Cache Statistics

```python
# Get detailed statistics
stats = cache_service.get_cache_statistics()

print(f"Total reads: {stats['total_reads']}")
print(f"Memory hits: {stats['memory_hits']}")
print(f"API calls: {stats['api_calls']}")
print(f"Cache hit rate: {stats['total_cache_hit_rate_pct']}%")
print(f"API calls saved: {stats['api_calls_saved']}")
print(f"Savings: {stats['savings_percentage']}%")
```

Example output:
```
Total reads: 100
Memory hits: 85
API calls: 15
Cache hit rate: 85.00%
API calls saved: 85
Savings: 85.00%
Current cache size: 45 entries
```

### Manual Cache Invalidation

```python
# Invalidate entire cache
cache_service.invalidate_cache()

# Invalidate specific spreadsheet
cache_service.invalidate_cache(spreadsheet_id="sheet-123")

# Invalidate specific range
cache_service.invalidate_cache(
    spreadsheet_id="sheet-123",
    range_name="Sheet1!A1:D10"
)
```

### Batch Operations

```python
# Read multiple sheets efficiently
requests = [
    ("sheet1", "Sheet1!A1:D10"),
    ("sheet2", "Sheet1!A1:D10"),
    ("sheet3", "Sheet1!A1:D10"),
]

dataframes = cache_service.batch_read_sheets_cached(requests)
```

## Cache File Format

### On-Disk Structure

Location: `.cache/sheets_cache.json`

```json
{
  "version": "1.0",
  "last_updated": "2025-10-05T14:30:00",
  "entries": {
    "spreadsheet-id-123:Sheet1!A1:D10": {
      "data": [
        {"Date": "2025-01-01", "Project": "PROJ-001", "Hours": 8},
        {"Date": "2025-01-02", "Project": "PROJ-001", "Hours": 7.5}
      ],
      "modified_time": "2025-10-05T10:00:00+00:00",
      "cached_at": "2025-10-05T10:00:05"
    }
  }
}
```

### Version Management

The cache file includes a version field for future compatibility:
- Current version: `1.0`
- Incompatible versions are ignored (cache rebuilt)
- Allows for cache format migrations

## Performance Characteristics

### Cache Operations

| Operation | Time Complexity | Notes |
|-----------|-----------------|-------|
| Memory lookup | O(1) | OrderedDict provides constant-time access |
| Modification time check | O(1) | Single Drive API call (metadata only) |
| Cache eviction (LRU) | O(1) | OrderedDict maintains insertion order |
| Disk save | O(n) | n = number of cached entries |
| Disk load | O(n) | n = number of cached entries |

### Typical Performance

**Without caching:**
- 30 timesheets × 2 ranges each = 60 API calls
- Average: 200ms per API call = 12 seconds total

**With caching (80% hit rate):**
- First run: 60 API calls = 12 seconds
- Subsequent runs: 12 API calls + 48 cache hits = 2.4 seconds
- **80% faster** on subsequent runs

## Thread Safety

The cache service is **thread-safe** for concurrent operations:

```python
import threading

def read_timesheet(spreadsheet_id):
    return cache_service.read_sheet_cached(
        spreadsheet_id,
        "Sheet1!A1:D10"
    )

# Multiple threads can safely access cache
threads = [
    threading.Thread(target=read_timesheet, args=(f"sheet{i}",))
    for i in range(10)
]

for t in threads:
    t.start()

for t in threads:
    t.join()
```

**Thread Safety Mechanisms:**
- `threading.Lock` protects cache updates
- Atomic disk writes (temp file + rename)
- No race conditions in LRU eviction

## Error Handling

### Corrupted Cache Files

```python
# Cache service handles corrupted files gracefully
# Logs error and continues with empty cache

# Example scenario:
# 1. .cache/sheets_cache.json is corrupted (invalid JSON)
# 2. Service logs error: "Failed to parse cache file (corrupted JSON)"
# 3. Service starts with empty cache
# 4. Normal operation continues
```

### Drive API Errors

```python
# If Drive API fails to get modification time:
# 1. Cache entry is considered invalid
# 2. Fresh data is fetched from Sheets API
# 3. Cache is not updated (to avoid caching stale data)
# 4. Operation completes successfully
```

### Disk Write Failures

```python
# If disk write fails (permissions, disk full, etc.):
# 1. Error is logged
# 2. Memory cache remains intact
# 3. Data is still returned to caller
# 4. No user-visible error
```

## Best Practices

### 1. Enable Caching for Production

```python
# In production .env:
ENABLE_SHEETS_CACHE=True
CACHE_AUTO_SAVE=True
```

### 2. Adjust Cache Size Based on Dataset

```python
# For 100+ timesheets:
CACHE_MAX_SIZE=200

# For small datasets:
CACHE_MAX_SIZE=50
```

### 3. Monitor Cache Performance

```python
# Periodically check cache statistics
stats = cache_service.get_cache_statistics()

if stats['total_cache_hit_rate_pct'] < 50:
    # Consider increasing cache size or checking
    # for frequent file modifications
    logger.warning(f"Low cache hit rate: {stats['total_cache_hit_rate_pct']}%")
```

### 4. Clear Cache After Bulk Updates

```python
# After bulk updating Google Sheets:
cache_service.invalidate_cache()

# Or invalidate specific sheets:
for sheet_id in updated_sheets:
    cache_service.invalidate_cache(spreadsheet_id=sheet_id)
```

### 5. Use Batch Operations for Efficiency

```python
# Instead of individual reads:
# DON'T DO THIS:
for sheet_id in sheet_ids:
    df = cache_service.read_sheet_cached(sheet_id, range_name)

# DO THIS:
requests = [(sheet_id, range_name) for sheet_id in sheet_ids]
dataframes = cache_service.batch_read_sheets_cached(requests)
```

## Troubleshooting

### Cache Not Working

**Symptom**: Every read calls the API (no cache hits)

**Solutions**:
1. Check cache is enabled: `ENABLE_SHEETS_CACHE=True`
2. Verify cache service is passed to readers
3. Check file permissions for cache directory
4. Review logs for cache errors

### High Cache Invalidation Rate

**Symptom**: Frequent cache invalidations

**Causes**:
- Files are being frequently modified
- System clock synchronization issues
- Multiple processes modifying same files

**Solutions**:
- Batch file updates to reduce modification frequency
- Sync system clock with NTP
- Coordinate file updates across processes

### Cache File Growing Too Large

**Symptom**: `.cache/sheets_cache.json` is very large

**Solutions**:
1. Reduce `CACHE_MAX_SIZE`
2. Clear old cache: `rm .cache/sheets_cache.json`
3. Invalidate unused entries periodically

### Permission Errors

**Symptom**: "Permission denied" when writing cache

**Solutions**:
1. Ensure `.cache/` directory exists and is writable
2. Check file ownership: `ls -la .cache/`
3. Set proper permissions: `chmod 755 .cache/`

## Technical Details

### RFC 3339 Timestamp Parsing

```python
# Google Drive API returns timestamps in RFC 3339 format:
# "2025-10-05T10:00:00.000Z"

# Python's datetime.fromisoformat() requires:
# "2025-10-05T10:00:00.000+00:00"

# Conversion:
if modified_time_str.endswith("Z"):
    modified_time_str = modified_time_str[:-1] + "+00:00"

modified_time = datetime.fromisoformat(modified_time_str)
```

### Atomic Disk Writes

```python
# Write to temp file
temp_fd, temp_path = tempfile.mkstemp(dir=cache_dir)
with os.fdopen(temp_fd, 'w') as f:
    json.dump(cache_data, f)

# Atomic rename (POSIX guarantees atomicity)
os.replace(temp_path, final_path)

# Result: Cache file is never corrupted,
# even if process is killed during write
```

### LRU Eviction with OrderedDict

```python
from collections import OrderedDict

# OrderedDict maintains insertion order
cache = OrderedDict()

# Access moves item to end (most recent)
cache.move_to_end(key)

# When full, remove first item (oldest)
oldest_key = next(iter(cache))
del cache[oldest_key]
```

## Future Enhancements

Potential improvements for future versions:

1. **TTL-based expiration**: Add time-based expiration in addition to modification-time
2. **Cache compression**: Compress large DataFrames to reduce disk usage
3. **Distributed caching**: Support multiple processes sharing cache (Redis, etc.)
4. **Smart prefetching**: Predict and prefetch likely-needed sheets
5. **Cache warming**: Preload frequently-used sheets on startup
6. **Metrics export**: Export statistics to Prometheus/Grafana

---

**Last Updated**: 2025-10-05
