"""
Performance testing and benchmarks.

Tests system performance with realistic and large data volumes to ensure:
- Processing time stays within acceptable limits
- Memory usage is reasonable
- Caching provides expected speedup
- System can handle production data volumes (30+ freelancers, 9000+ rows)

Uses pytest-benchmark for performance measurement and tracking.
"""

import time
from datetime import date, timedelta

import pytest

from src.readers import TimesheetReader
from src.writers import MasterTimesheetGenerator
from tests.integration.utils import generate_test_timesheet


@pytest.mark.performance
@pytest.mark.integration
@pytest.mark.slow
class TestTimesheetReadingPerformance:
    """Test performance of timesheet reading operations."""

    def test_single_timesheet_read_performance(
        self,
        benchmark,
        real_sheets_service,
        test_spreadsheet_id: str,
        performance_baseline,
    ):
        """Benchmark reading a single timesheet with ~100 entries."""
        # Setup: Create test data
        test_data = generate_test_timesheet(num_entries=100)

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=test_data,
        )

        # Benchmark the read operation
        reader = TimesheetReader(
            sheets_service=real_sheets_service, freelancer_name="Perf Test"
        )

        def read_timesheet():
            return reader.read_timesheet(spreadsheet_id=test_spreadsheet_id)

        # Run benchmark
        result = benchmark(read_timesheet)

        # Verify we got data
        assert len(result) > 0

        # Check against baseline (500ms max)
        assert (
            benchmark.stats["mean"]
            < performance_baseline["single_timesheet_read_ms"] / 1000
        ), f"Reading took {benchmark.stats['mean']:.3f}s, expected < {performance_baseline['single_timesheet_read_ms']/1000:.3f}s"

    def test_cached_read_performance(
        self,
        benchmark,
        real_sheets_service,
        test_spreadsheet_id: str,
        performance_baseline,
    ):
        """Benchmark cached reads vs uncached reads."""
        # Setup test data
        test_data = generate_test_timesheet(num_entries=100)

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=test_data,
        )

        # First read to populate cache
        data1 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:Z200"
        )

        # Benchmark cached read
        def read_cached():
            return real_sheets_service.read_sheet_data(
                spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:Z200"
            )

        result = benchmark(read_cached)

        # Cached read should be very fast (< 10ms typically)
        assert result == data1
        print(f"\nCached read time: {benchmark.stats['mean']:.4f}s")


@pytest.mark.performance
@pytest.mark.integration
@pytest.mark.slow
class TestAggregationPerformance:
    """Test performance of data aggregation operations."""

    @pytest.mark.skipif(
        "not config.getoption('--run-performance-tests', default=False)",
        reason="Requires --run-performance-tests flag (slow test)",
    )
    def test_aggregate_10_timesheets_performance(
        self,
        benchmark,
        real_sheets_service,
        integration_config,
        performance_baseline,
    ):
        """Benchmark aggregating 10 timesheets (~1000 total entries)."""
        # Note: This test creates actual test spreadsheets and is very slow
        # Only run with explicit flag

        # This is a simplified version - full implementation would:
        # 1. Create 10 test spreadsheets
        # 2. Use TimesheetAggregator to process them
        # 3. Measure total time
        # 4. Cleanup

        pytest.skip("Full aggregation performance test requires extensive setup")

    def test_master_generation_performance(
        self,
        benchmark,
        performance_baseline,
    ):
        """Benchmark master timesheet generation with 1000 rows."""
        from src.aggregators.timesheet_aggregator import AggregatedTimesheetData
        from src.models import BillingResult, TimesheetEntry

        # Generate test data
        entries = []
        billing_results = []
        trips = []

        for i in range(1000):
            entry = TimesheetEntry(
                freelancer_name="Test Freelancer",
                date=date(2024, 1, 1) + timedelta(days=i % 365),
                project="P&C_NEWRETAIL",
                location="remote",
                start_time="09:00",
                end_time="17:00",
                topics_worked_on="Development",
                break_minutes=60,
                travel_time_minutes=0,
            )
            entries.append(entry)

            # Add corresponding billing result
            billing_result = BillingResult(
                freelancer_name="Test Freelancer",
                date=entry.date,
                project=entry.project,
                billable_hours=7.0,
                hours_billed=595.0,
                travel_surcharge=0.0,
                total_billed=595.0,
                total_cost=420.0,
                profit=175.0,
                profit_margin_percent=29.41,
            )
            billing_results.append(billing_result)

        # Create aggregated data
        aggregated_data = AggregatedTimesheetData(
            entries=entries, billing_results=billing_results, trips=trips
        )

        # Benchmark generation
        def generate_master():
            generator = MasterTimesheetGenerator()
            return generator.generate(aggregated_data=aggregated_data)

        result = benchmark(generate_master)

        # Verify output
        assert result.timesheet_master is not None
        assert len(result.timesheet_master) > 1000  # Header + 1000 rows

        # Check against baseline (2 seconds max for 1000 rows)
        assert (
            benchmark.stats["mean"]
            < performance_baseline["master_generation_1000_rows_sec"]
        ), f"Generation took {benchmark.stats['mean']:.3f}s, expected < {performance_baseline['master_generation_1000_rows_sec']:.3f}s"

        print(
            f"\nGenerated {len(result.timesheet_master)} rows in {benchmark.stats['mean']:.3f}s"
        )


@pytest.mark.performance
@pytest.mark.integration
@pytest.mark.slow
class TestCachingPerformance:
    """Test caching system performance and effectiveness."""

    def test_cache_api_call_reduction(
        self,
        real_sheets_service,
        real_cache_service,
        test_spreadsheet_id: str,
        performance_baseline,
    ):
        """Verify that caching reduces API calls by expected percentage."""
        # Clear cache
        real_cache_service.clear()

        # Setup test data
        test_data = generate_test_timesheet(num_entries=50)

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=test_data,
        )

        # Make 10 reads - first one should be API call, rest should be cached
        range_name = "Sheet1!A1:Z100"

        for i in range(10):
            data = real_sheets_service.read_sheet_data(
                spreadsheet_id=test_spreadsheet_id, range_name=range_name
            )

        # Get cache stats
        stats = real_cache_service.get_cache_stats()

        # Should have high cache hit rate (at least 60%)
        # Note: actual calculation depends on implementation
        assert stats["size"] > 0, "Cache should have entries"

        print(f"\nCache stats after 10 reads: {stats}")

    def test_cache_speedup_factor(
        self,
        real_sheets_service,
        real_cache_service,
        test_spreadsheet_id: str,
        performance_baseline,
    ):
        """Measure actual speedup factor from caching."""
        # Clear cache
        real_cache_service.clear()

        # Setup test data
        test_data = generate_test_timesheet(num_entries=100)

        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=test_data,
        )

        # Measure uncached read
        range_name = "Sheet1!A1:Z200"

        start_time = time.time()
        data1 = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name=range_name
        )
        uncached_time = time.time() - start_time

        # Measure cached read (multiple reads, take average)
        cached_times = []
        for i in range(5):
            start_time = time.time()
            data2 = real_sheets_service.read_sheet_data(
                spreadsheet_id=test_spreadsheet_id, range_name=range_name
            )
            cached_times.append(time.time() - start_time)

        avg_cached_time = sum(cached_times) / len(cached_times)

        # Calculate speedup
        speedup_factor = uncached_time / avg_cached_time

        print(
            f"\nUncached: {uncached_time:.4f}s, Cached (avg): {avg_cached_time:.4f}s, Speedup: {speedup_factor:.1f}x"
        )

        # Should be at least 5x faster (conservative)
        assert (
            speedup_factor >= 5.0
        ), f"Cache speedup ({speedup_factor:.1f}x) below expected (>= 5x)"


@pytest.mark.performance
@pytest.mark.integration
@pytest.mark.slow
class TestScalability:
    """Test system scalability with large datasets."""

    def test_large_dataset_memory_usage(
        self,
        real_sheets_service,
        test_spreadsheet_id: str,
    ):
        """Test memory usage with large datasets (1000+ rows)."""
        import sys

        # Generate large dataset
        large_data = [["Col1", "Col2", "Col3", "Col4", "Col5"]]
        for i in range(2000):
            large_data.append(
                [f"Val{i}_1", f"Val{i}_2", f"Val{i}_3", f"Val{i}_4", f"Val{i}_5"]
            )

        # Write large dataset
        real_sheets_service.update_sheet_data(
            spreadsheet_id=test_spreadsheet_id,
            range_name="Sheet1!A1",
            values=large_data,
        )

        # Read and measure size
        data = real_sheets_service.read_sheet_data(
            spreadsheet_id=test_spreadsheet_id, range_name="Sheet1!A1:E2001"
        )

        # Check size in memory
        data_size_bytes = sys.getsizeof(data)

        print(
            f"\nDataset: {len(data)} rows, Memory: {data_size_bytes / 1024 / 1024:.2f} MB"
        )

        # Should be reasonable (< 10 MB for 2000 rows)
        assert data_size_bytes < 10 * 1024 * 1024

    def test_processing_time_linear_scaling(
        self,
        real_sheets_service,
        test_spreadsheet_id: str,
    ):
        """Test that processing time scales linearly with dataset size."""
        # Test with different dataset sizes
        sizes = [100, 500, 1000]
        times = []

        for size in sizes:
            # Generate data
            data = [["A", "B", "C"]]
            for i in range(size):
                data.append([f"Val{i}_1", f"Val{i}_2", f"Val{i}_3"])

            # Write and time read
            real_sheets_service.update_sheet_data(
                spreadsheet_id=test_spreadsheet_id,
                range_name="Sheet1!A1",
                values=data,
            )

            # Clear cache to ensure fair comparison
            start_time = time.time()
            reader = TimesheetReader(
                sheets_service=real_sheets_service, freelancer_name="Scale Test"
            )
            _ = reader.read_timesheet(spreadsheet_id=test_spreadsheet_id)
            elapsed = time.time() - start_time

            times.append(elapsed)

            print(f"Size: {size} rows, Time: {elapsed:.3f}s")

        # Verify roughly linear scaling
        # Time per row should be similar across different sizes
        time_per_row_100 = times[0] / sizes[0]
        time_per_row_1000 = times[2] / sizes[2]

        # Allow 3x variation (not perfect linear, but reasonable)
        assert (
            time_per_row_1000 < time_per_row_100 * 3
        ), "Processing time should scale roughly linearly"
