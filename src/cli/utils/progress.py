"""Progress tracking utilities for CLI."""

from typing import List, Optional

import click


class ProgressTracker:
    """Track progress through multiple stages of a process.

    Attributes:
        stages: List of stage names
        total_stages: Total number of stages
        current_stage: Current stage index (0-based)
    """

    def __init__(self, stages: List[str]):
        """Initialize progress tracker with stages.

        Args:
            stages: List of stage names
        """
        self.stages = stages
        self.total_stages = len(stages)
        self.current_stage = 0

    def advance(self, message: Optional[str] = None):
        """Advance to the next stage.

        Args:
            message: Optional message to display when advancing
        """
        if message:
            click.echo(f"  {message}")
        self.current_stage += 1

    def get_current_message(self) -> str:
        """Get the current stage message with progress indicator.

        Returns:
            Formatted message with stage number and name
        """
        if self.current_stage < self.total_stages:
            stage_name = self.stages[self.current_stage]
            return f"[{self.current_stage + 1}/{self.total_stages}] {stage_name}"
        return f"[{self.total_stages}/{self.total_stages}] Complete"

    def is_complete(self) -> bool:
        """Check if all stages are complete.

        Returns:
            True if all stages are complete, False otherwise
        """
        return self.current_stage >= self.total_stages


def create_progress_bar(length: int, label: str = "Processing"):
    """Create a Click progress bar.

    Args:
        length: Total number of items to process
        label: Label to display with the progress bar

    Returns:
        Click progress bar context manager
    """
    return click.progressbar(length=length, label=label, show_pos=True)
