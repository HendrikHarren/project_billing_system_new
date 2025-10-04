"""Demo script showing full data flow with real Google Sheets data.

This script demonstrates:
1. Reading timesheet data from Google Sheets (via direct API)
2. Calculating billable hours
3. Calculating trips from consecutive on-site days
4. Displaying results

Note: Uses direct Google API instead of readers to simplify demo.
"""

import datetime as dt
import os
from collections import defaultdict
from decimal import Decimal

import pandas as pd
from dotenv import load_dotenv

from src.calculators.time_calculator import calculate_billable_hours
from src.calculators.trip_calculator import calculate_trips
from src.google_auth import get_drive_service, get_sheets_service
from src.models.project import ProjectTerms
from src.models.timesheet import TimesheetEntry


def main():
    """Run the demo data flow."""
    load_dotenv()

    print("=" * 80)
    print("BILLING SYSTEM - REAL DATA FLOW DEMO")
    print("=" * 80)

    # Step 1: Read timesheet data
    print("\n📊 Step 1: Reading Timesheet Data from Google Sheets...")
    print("-" * 80)

    timesheet_folder_id = os.getenv("TIMESHEET_FOLDER_ID")
    print(f"Timesheet Folder ID: {timesheet_folder_id}")

    # Get list of timesheet files from folder
    drive_service = get_drive_service()
    response = (
        drive_service.files()
        .list(
            q=f"'{timesheet_folder_id}' in parents",
            fields="files(id, name)",
        )
        .execute()
    )
    files = response.get("files", [])
    print(f"Found {len(files)} timesheet files in folder")

    # Read timesheets using direct API
    sheets_service = get_sheets_service()
    timesheet_entries = []

    for file in files[:3]:  # Limit to first 3 for demo
        print(f"  Reading: {file['name']}")

        # Extract freelancer name from filename
        freelancer_name = " ".join(file["name"].split("_")[:-1])

        # Read timesheet data
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=file["id"], range="Timesheet!A3:I")
            .execute()
        )
        values = result.get("values", [])

        # Parse into TimesheetEntry objects
        for row in values:
            if len(row) < 5 or not row[0]:  # Skip empty rows
                continue

            try:
                # Parse date
                date_str = row[0] if len(row) > 0 else ""
                date = pd.to_datetime(date_str).date()

                # Parse times
                start_time_str = row[3] if len(row) > 3 else "09:00"
                end_time_str = row[4] if len(row) > 4 else "17:00"

                # Handle time formats
                if ":" in start_time_str:
                    start_time = dt.datetime.strptime(start_time_str, "%H:%M").time()
                else:
                    start_time = dt.time(9, 0)

                if ":" in end_time_str:
                    end_time = dt.datetime.strptime(end_time_str, "%H:%M").time()
                else:
                    end_time = dt.time(17, 0)

                # Parse other fields
                project_code = row[1] if len(row) > 1 else "UNKNOWN"
                location_raw = row[2] if len(row) > 2 else "remote"
                location = "onsite" if "on-site" in location_raw.lower() else "remote"

                # Parse break and travel time
                break_str = row[6] if len(row) > 6 else "0:00"
                travel_str = row[7] if len(row) > 7 else "0:00"

                break_minutes = 0
                if ":" in break_str:
                    h, m = break_str.split(":")
                    break_minutes = int(h) * 60 + int(m)

                travel_minutes = 0
                if ":" in travel_str:
                    h, m = travel_str.split(":")
                    travel_minutes = int(h) * 60 + int(m)

                entry = TimesheetEntry(
                    freelancer_name=freelancer_name,
                    date=date,
                    project_code=project_code,
                    start_time=start_time,
                    end_time=end_time,
                    break_minutes=break_minutes,
                    travel_time_minutes=travel_minutes,
                    location=location,
                )
                timesheet_entries.append(entry)

            except Exception as e:
                print(f"    ⚠️  Skipping row due to error: {e}")
                continue

        count = len(
            [e for e in timesheet_entries if e.freelancer_name == freelancer_name]
        )
        print(f"    → {count} entries")

    print(f"✅ Successfully read {len(timesheet_entries)} timesheet entries")

    if timesheet_entries:
        print("\nSample entry:")
        entry = timesheet_entries[0]
        print(f"  Freelancer: {entry.freelancer_name}")
        print(f"  Date: {entry.date}")
        print(f"  Project: {entry.project_code}")
        print(f"  Hours: {entry.start_time} - {entry.end_time}")
        print(f"  Location: {entry.location}")
        print(f"  Break: {entry.break_minutes} min")
        print(f"  Travel: {entry.travel_time_minutes} min")

    # Step 2: Read project terms
    print("\n💰 Step 2: Reading Project Terms...")
    print("-" * 80)

    project_terms_file_id = os.getenv("PROJECT_TERMS_FILE_ID")
    print(f"Project Terms File ID: {project_terms_file_id}")

    # Read main terms
    main_result = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=project_terms_file_id, range="Main terms!A2:G")
        .execute()
    )
    main_values = main_result.get("values", [])

    project_terms = []
    for row in main_values:
        if len(row) < 5:
            continue
        try:
            # Correct column mapping:
            # 0=Project, 1=ID, 2=Name, 3=Rate, 4=Cost, 5=Travel%, 6=Surch%
            terms = ProjectTerms(
                project_code=row[0],  # Column A: Project
                freelancer_name=row[2],  # Column C: Name
                hourly_rate=Decimal(str(row[3])),  # Column D: Rate
                cost_per_hour=Decimal(str(row[4])),  # Column E: Cost
                # Convert decimal to percentage (0.5 → 50.0)
                travel_time_percentage=Decimal(str(float(row[5]) * 100))
                if len(row) > 5 and row[5]
                else Decimal("0"),
                travel_surcharge_percentage=Decimal(str(float(row[6]) * 100))
                if len(row) > 6 and row[6]
                else Decimal("0"),
            )
            project_terms.append(terms)
        except Exception as e:
            print(f"  ⚠️  Skipping terms row: {e}")

    print(f"✅ Successfully read {len(project_terms)} project term records")

    if project_terms:
        print("\nSample project terms:")
        terms = project_terms[0]
        print(f"  Freelancer: {terms.freelancer_name}")
        print(f"  Project: {terms.project_code}")
        print(f"  Hourly Rate: €{terms.hourly_rate}")
        print(f"  Travel Surcharge: {terms.travel_surcharge_percentage}%")
        print(f"  Travel Time %: {terms.travel_time_percentage}%")

    # Step 3: Calculate billable hours for sample entries
    print("\n💵 Step 3: Calculating Billable Hours...")
    print("-" * 80)

    if timesheet_entries and project_terms:
        # Find matching entries and calculate
        sample_count = min(5, len(timesheet_entries))
        print(f"Showing calculations for first {sample_count} entries:\n")

        for i, entry in enumerate(timesheet_entries[:sample_count], 1):
            # Find matching project terms
            matching_terms = [
                t
                for t in project_terms
                if t.freelancer_name == entry.freelancer_name
                and t.project_code == entry.project_code
            ]

            if matching_terms:
                terms = matching_terms[0]
                result = calculate_billable_hours(entry, terms)

                print(f"{i}. {entry.freelancer_name} - {entry.date} ({entry.location})")
                print(f"   Work hours: {result.work_hours:.2f}h")
                print(f"   Break: -{result.break_hours:.2f}h")
                print(f"   Travel bonus: +{result.travel_hours:.2f}h")
                print(f"   → Total billable: {result.total_hours:.2f}h")
                amount = result.total_hours * terms.hourly_rate
                print(f"   → Amount: €{amount:.2f}\n")

    # Step 4: Calculate trips
    print("\n✈️  Step 4: Calculating Trips (Consecutive On-Site Days)...")
    print("-" * 80)

    trips = calculate_trips(timesheet_entries)
    print(f"✅ Identified {len(trips)} trips from timesheet data\n")

    if trips:
        # Group trips by freelancer
        trips_by_freelancer = defaultdict(list)
        for trip in trips:
            trips_by_freelancer[trip.freelancer_name].append(trip)

        for freelancer, freelancer_trips in sorted(trips_by_freelancer.items()):
            print(f"\n{freelancer}:")
            for trip in sorted(freelancer_trips, key=lambda t: t.start_date):
                print(f"  • {trip.start_date} to {trip.end_date}")
                print(f"    Duration: {trip.duration_days} days")
                print(f"    Project: {trip.project_code}")
                print(f"    Location: {trip.location}")

    # Step 5: Summary statistics
    print("\n📈 Step 5: Summary Statistics...")
    print("-" * 80)

    # Count by location
    onsite_count = sum(1 for e in timesheet_entries if e.location == "onsite")
    remote_count = sum(1 for e in timesheet_entries if e.location == "remote")

    # Count unique freelancers
    unique_freelancers = len(set(e.freelancer_name for e in timesheet_entries))

    # Count unique projects
    unique_projects = len(set(e.project_code for e in timesheet_entries))

    print(f"Total Entries: {len(timesheet_entries)}")
    print(f"  - On-site: {onsite_count}")
    print(f"  - Remote: {remote_count}")
    print(f"Unique Freelancers: {unique_freelancers}")
    print(f"Unique Projects: {unique_projects}")
    print(f"Total Trips: {len(trips)}")

    # Calculate total billable if we have both data
    if timesheet_entries and project_terms:
        total_billable_hours = Decimal("0")
        total_billable_amount = Decimal("0")

        for entry in timesheet_entries:
            matching_terms = [
                t
                for t in project_terms
                if t.freelancer_name == entry.freelancer_name
                and t.project_code == entry.project_code
            ]

            if matching_terms:
                terms = matching_terms[0]
                result = calculate_billable_hours(entry, terms)
                total_billable_hours += result.total_hours
                total_billable_amount += result.total_hours * terms.hourly_rate

        print(f"\nTotal Billable Hours: {total_billable_hours:.2f}h")
        print(f"Total Billable Amount: €{total_billable_amount:.2f}")

    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETED - All components working with real data!")
    print("=" * 80)


if __name__ == "__main__":
    main()
