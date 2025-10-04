"""Trip calculator for billing system.

This module implements the business logic for grouping consecutive on-site days
into trips, matching the Jupyter notebook algorithm exactly.

The algorithm groups timesheet entries by:
- Filtering to on-site only (location != "remote")
- Sorting by freelancer, project, location, date
- Detecting breaks in consecutive days
- Creating Trip objects for each group
"""

from typing import List

from src.models.timesheet import TimesheetEntry
from src.models.trip import Trip


def calculate_trips(entries: List[TimesheetEntry]) -> List[Trip]:
    """Calculate trips from timesheet entries by grouping consecutive on-site days.

    This function implements the trip grouping logic from the Jupyter notebook:
    - Filters to on-site entries only (location != "remote")
    - Groups consecutive days for same freelancer/project/location
    - Consecutive means date difference of 0 or 1 day
    - Creates Trip objects with start_date, end_date, and duration

    Args:
        entries: List of timesheet entries to process

    Returns:
        List of Trip objects representing grouped consecutive on-site days

    Example:
        >>> entries = [
        ...     TimesheetEntry(
        ...         freelancer_name="John Doe",
        ...         date=date(2023, 6, 12),
        ...         project_code="PROJ-001",
        ...         start_time=time(9, 0),
        ...         end_time=time(17, 0),
        ...         break_minutes=30,
        ...         travel_time_minutes=60,
        ...         location="Berlin",
        ...     ),
        ...     TimesheetEntry(
        ...         freelancer_name="John Doe",
        ...         date=date(2023, 6, 13),
        ...         project_code="PROJ-001",
        ...         start_time=time(9, 0),
        ...         end_time=time(17, 0),
        ...         break_minutes=30,
        ...         travel_time_minutes=60,
        ...         location="Berlin",
        ...     ),
        ... ]
        >>> trips = calculate_trips(entries)
        >>> len(trips)
        1
        >>> trips[0].duration_days
        2
    """
    # Return empty list for empty input
    if not entries:
        return []

    # Filter to on-site entries only (exclude remote work)
    onsite_entries = [e for e in entries if e.location != "remote"]

    if not onsite_entries:
        return []

    # Sort by freelancer, project, location, then date
    # This ensures we process entries in the correct order for grouping
    sorted_entries = sorted(
        onsite_entries,
        key=lambda e: (e.freelancer_name, e.project_code, e.location, e.date),
    )

    # Group consecutive days into trips
    trips: List[Trip] = []
    current_group: List[TimesheetEntry] = []

    for entry in sorted_entries:
        if not current_group:
            # Start first group
            current_group.append(entry)
        else:
            # Check if this entry continues the current trip
            last_entry = current_group[-1]

            # Calculate date difference
            date_diff = (entry.date - last_entry.date).days

            # Check if entry belongs to same trip
            # Same freelancer, project, location and consecutive (0-1 day)
            is_same_trip = (
                entry.freelancer_name == last_entry.freelancer_name
                and entry.project_code == last_entry.project_code
                and entry.location == last_entry.location
                and date_diff <= 1
            )

            if is_same_trip:
                # Continue trip (skip if same day to handle duplicates)
                if date_diff > 0:
                    current_group.append(entry)
            else:
                # Start new trip - first save the current trip
                trips.append(_create_trip_from_group(current_group))
                current_group = [entry]

    # Don't forget the last group
    if current_group:
        trips.append(_create_trip_from_group(current_group))

    return trips


def _create_trip_from_group(group: List[TimesheetEntry]) -> Trip:
    """Create Trip from consecutive timesheet entries.

    Args:
        group: List of timesheet entries representing consecutive days

    Returns:
        Trip object with start_date, end_date calculated from the group

    Raises:
        ValueError: If group is empty
    """
    if not group:
        raise ValueError("Cannot create trip from empty group")

    first_entry = group[0]
    last_entry = group[-1]

    return Trip(
        freelancer_name=first_entry.freelancer_name,
        project_code=first_entry.project_code,
        location=first_entry.location,
        start_date=first_entry.date,
        end_date=last_entry.date,
    )
