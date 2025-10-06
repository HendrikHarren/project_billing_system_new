"""
Test data generator for integration tests.

This module provides utilities to generate realistic test data for:
- Timesheets with various scenarios
- Large datasets for performance testing
- Edge cases (overnight shifts, year boundaries, etc.)
"""

import random
from datetime import date, timedelta
from typing import Any, List, Tuple


def generate_test_timesheet(
    freelancer_name: str = "Test Freelancer",
    project_code: str = "P&C_NEWRETAIL",
    start_date: date = None,
    num_entries: int = 20,
    include_overnight: bool = False,
    include_weekends: bool = False,
    include_trips: bool = False,
) -> List[List[Any]]:
    """
    Generate a realistic test timesheet with various scenarios.

    Args:
        freelancer_name: Name of the freelancer
        project_code: Project code for entries
        start_date: Start date for timesheet (defaults to current month)
        num_entries: Number of timesheet entries to generate
        include_overnight: Include overnight shift scenarios
        include_weekends: Include weekend work
        include_trips: Include consecutive on-site days (trips)

    Returns:
        List[List[Any]]: Timesheet data with headers and entries
    """
    if start_date is None:
        start_date = date.today().replace(day=1)

    headers = [
        "Date",
        "Project",
        "Location",
        "Start Time",
        "End Time",
        "Topics worked on",
        "Break",
        "Travel time",
    ]

    data = [headers]
    current_date = start_date

    # Generate entries
    trip_days = 0  # Track consecutive on-site days for trips
    for i in range(num_entries):
        # Skip weekends unless include_weekends is True
        while current_date.weekday() >= 5 and not include_weekends:
            current_date += timedelta(days=1)

        # Determine location
        if include_trips and trip_days > 0:
            location = "On-site"
            trip_days -= 1
        elif include_trips and random.random() < 0.3:  # 30% chance to start a trip
            location = "On-site"
            trip_days = random.randint(2, 4)  # 2-4 day trips
        else:
            location = "Off-site" if random.random() < 0.7 else "On-site"

        # Generate realistic work times
        if include_overnight and random.random() < 0.1:  # 10% overnight shifts
            start_time = "22:00"
            end_time = "06:00"  # Next day
        else:
            start_hour = random.choice([8, 9, 10])
            end_hour = random.choice([17, 18, 19])
            start_time = f"{start_hour:02d}:00"
            end_time = f"{end_hour:02d}:00"

        # Generate break and travel time
        break_minutes = random.choice([30, 45, 60])
        break_time = f"00:{break_minutes:02d}" if break_minutes < 60 else "01:00"

        travel_minutes = random.choice([0, 60, 90, 120]) if location == "On-site" else 0
        travel_time = (
            f"{travel_minutes // 60:02d}:{travel_minutes % 60:02d}"
            if travel_minutes > 0
            else "00:00"
        )

        # Generate topics
        topics = random.choice(
            [
                "Development work",
                "Client meeting",
                "Code review",
                "Testing",
                "Documentation",
                "Workshop",
                "Planning",
            ]
        )

        data.append(
            [
                current_date.strftime("%Y-%m-%d"),
                project_code,
                location,
                start_time,
                end_time,
                topics,
                break_time,
                travel_time,
            ]
        )

        current_date += timedelta(days=1)

    return data


def generate_large_timesheet_data(
    num_freelancers: int = 30, entries_per_freelancer: int = 300
) -> List[Tuple[str, List[List[Any]]]]:
    """
    Generate large dataset for performance testing.

    This generates data similar to production volumes (30 freelancers,
    ~300 entries each = ~9000 total rows).

    Args:
        num_freelancers: Number of freelancers to generate data for
        entries_per_freelancer: Number of entries per freelancer

    Returns:
        List[Tuple[str, List[List[Any]]]]: List of (freelancer_name, timesheet_data)
    """
    datasets = []
    project_codes = [
        "P&C_NEWRETAIL",
        "PROJECT_ALPHA",
        "PROJECT_BETA",
        "CONSULTING_GAMMA",
    ]

    for i in range(num_freelancers):
        freelancer_name = f"Freelancer_{i + 1:03d}"
        project = random.choice(project_codes)

        timesheet_data = generate_test_timesheet(
            freelancer_name=freelancer_name,
            project_code=project,
            num_entries=entries_per_freelancer,
            include_overnight=True,
            include_trips=True,
        )

        datasets.append((freelancer_name, timesheet_data))

    return datasets


def generate_edge_case_timesheet() -> List[List[Any]]:
    """
    Generate timesheet with edge cases for testing.

    Includes:
    - Overnight shifts
    - Year boundary transitions
    - Maximum and minimum work hours
    - Zero break scenarios
    - High travel time scenarios

    Returns:
        List[List[Any]]: Timesheet data with edge cases
    """
    headers = [
        "Date",
        "Project",
        "Location",
        "Start Time",
        "End Time",
        "Topics worked on",
        "Break",
        "Travel time",
    ]

    data = [
        headers,
        # Overnight shift
        [
            "2024-12-31",
            "PROJECT_ALPHA",
            "On-site",
            "22:00",
            "06:00",
            "Night shift",
            "00:30",
            "02:00",
        ],
        # Year boundary
        [
            "2024-12-31",
            "PROJECT_ALPHA",
            "Off-site",
            "09:00",
            "17:00",
            "Year-end work",
            "01:00",
            "00:00",
        ],
        [
            "2025-01-01",
            "PROJECT_ALPHA",
            "Off-site",
            "10:00",
            "16:00",
            "New year planning",
            "00:30",
            "00:00",
        ],
        # Maximum hours (12-hour shift)
        [
            "2025-01-02",
            "P&C_NEWRETAIL",
            "On-site",
            "08:00",
            "20:00",
            "Long shift",
            "01:00",
            "03:00",
        ],
        # Minimum hours (4-hour shift)
        [
            "2025-01-03",
            "P&C_NEWRETAIL",
            "Off-site",
            "14:00",
            "18:00",
            "Short meeting",
            "00:00",
            "00:00",
        ],
        # Zero break
        [
            "2025-01-06",
            "PROJECT_ALPHA",
            "On-site",
            "09:00",
            "17:00",
            "Intensive work",
            "00:00",
            "02:00",
        ],
        # High travel time
        [
            "2025-01-07",
            "P&C_NEWRETAIL",
            "On-site",
            "08:00",
            "18:00",
            "Far client",
            "01:00",
            "04:00",
        ],
    ]

    return data


def generate_project_terms_data(num_projects: int = 5) -> List[List[Any]]:
    """
    Generate realistic project terms data for testing.

    Args:
        num_projects: Number of project-freelancer combinations

    Returns:
        List[List[Any]]: Project terms data with headers
    """
    headers = [
        "Project",
        "Consultant_ID",
        "Name",
        "Rate",
        "Cost",
        "Share of travel as work",
        "surcharge for travel",
    ]

    data = [headers]

    project_codes = [
        "P&C_NEWRETAIL",
        "PROJECT_ALPHA",
        "PROJECT_BETA",
        "CONSULTING_GAMMA",
    ]
    freelancer_names = [f"Freelancer_{i + 1:03d}" for i in range(10)]

    for i in range(num_projects):
        project = random.choice(project_codes)
        freelancer = random.choice(freelancer_names)
        rate = random.randint(75, 120)
        cost = int(rate * random.uniform(0.6, 0.8))
        travel_share = random.choice([0.5, 0.75, 1.0])
        travel_surcharge = random.choice([0.10, 0.15, 0.20])

        data.append(
            [
                project,
                f"C{i + 1:03d}",
                freelancer,
                rate,
                cost,
                travel_share,
                travel_surcharge,
            ]
        )

    return data


def generate_trip_terms_data() -> List[List[Any]]:
    """
    Generate trip reimbursement terms data for testing.

    Returns:
        List[List[Any]]: Trip terms data with headers
    """
    return [
        ["Location", "Trip Duration", "Trip Reimbursement"],
        ["Paris On-site", "1", "450"],
        ["Paris On-site", "2", "650"],
        ["Paris On-site", "3", "850"],
        ["Paris On-site", "4", "1000"],
        ["Berlin On-site", "1", "400"],
        ["Berlin On-site", "2", "600"],
        ["London On-site", "1", "500"],
        ["London On-site", "2", "700"],
    ]
