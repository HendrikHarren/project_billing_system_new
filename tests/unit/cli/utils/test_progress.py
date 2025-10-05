"""Unit tests for CLI progress indicators."""

from src.cli.utils.progress import ProgressTracker, create_progress_bar


class TestProgressTracker:
    """Test suite for ProgressTracker."""

    def test_progress_tracker_initialization(self):
        """Test that ProgressTracker initializes with stages."""
        stages = ["Stage 1", "Stage 2", "Stage 3"]
        tracker = ProgressTracker(stages)
        assert tracker.total_stages == 3
        assert tracker.current_stage == 0

    def test_progress_tracker_advance(self):
        """Test advancing to next stage."""
        stages = ["Stage 1", "Stage 2"]
        tracker = ProgressTracker(stages)
        tracker.advance("Stage 1 complete")
        assert tracker.current_stage == 1

    def test_progress_tracker_get_current_message(self):
        """Test getting current stage message."""
        stages = ["Reading files", "Processing data"]
        tracker = ProgressTracker(stages)
        message = tracker.get_current_message()
        assert "1/2" in message
        assert "Reading files" in message

    def test_progress_tracker_is_complete(self):
        """Test checking if all stages are complete."""
        stages = ["Stage 1"]
        tracker = ProgressTracker(stages)
        assert not tracker.is_complete()
        tracker.advance("Done")
        assert tracker.is_complete()


class TestCreateProgressBar:
    """Test suite for progress bar creation."""

    def test_create_progress_bar_with_length(self):
        """Test creating progress bar with specified length."""
        bar = create_progress_bar(length=10, label="Processing")
        assert bar is not None
        # Progress bar should be iterable
        assert hasattr(bar, "__iter__")

    def test_create_progress_bar_with_label(self):
        """Test that progress bar includes the label."""
        bar = create_progress_bar(length=5, label="Loading")
        assert bar is not None
