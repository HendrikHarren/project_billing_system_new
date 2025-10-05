"""Project terms reader for extracting billing terms from Google Sheets.

This module provides functionality to read and cache project-specific billing
terms and trip reimbursement rules from Google Sheets.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Import TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from src.models.project import ProjectTerms
from src.services.google_sheets_service import GoogleSheetsService

if TYPE_CHECKING:
    from src.services.sheets_cache_service import SheetsCacheService

logger = logging.getLogger(__name__)


class ProjectTermsReader:
    """Reader for extracting project billing terms from Google Sheets.

    This class handles reading project-specific billing terms and trip
    reimbursement rules from Google Sheets, with in-memory caching for
    performance optimization.

    The expected sheet structure:

    Main Terms Sheet (default: "Project Terms"):
    ```
    Freelancer | Project | Rate | Travel % | Time % | Cost/Hr
    ----------|---------|------|----------|--------|--------
    John Doe  | PROJ-001| 85.00| 15.0     | 50.0   | 60.00
    ```

    Trip Terms Sheet (default: "Trip Terms"):
    ```
    Min Days | Max Days | Reimbursement Type | Amount per Day
    ---------|----------|-------------------|----------------
    1        | 2        | Per Diem          | 50.00
    3        | 7        | Per Diem          | 45.00
    ```

    Attributes:
        sheets_service: Google Sheets service for data access
        spreadsheet_id: The ID of the spreadsheet containing terms
        cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)
        cache_service: Optional modification-time-based cache service

    Example:
        >>> from src.services.google_sheets_service import GoogleSheetsService
        >>> sheets_service = GoogleSheetsService()
        >>> reader = ProjectTermsReader(sheets_service, "spreadsheet-id-123")
        >>> terms = reader.get_project_terms("John Doe", "PROJ-001")
        >>> terms.hourly_rate
        Decimal('85.00')
    """

    def __init__(
        self,
        sheets_service: GoogleSheetsService,
        spreadsheet_id: str,
        cache_ttl: int = 3600,
        cache_service: Optional["SheetsCacheService"] = None,
    ):
        """Initialize the project terms reader.

        Args:
            sheets_service: Google Sheets service instance for data access
            spreadsheet_id: The ID of the spreadsheet containing project terms
            cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)
            cache_service: Optional modification-time-based cache service
        """
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
        self.cache_ttl = cache_ttl
        self.cache_service = cache_service

        # Cache storage (in-memory TTL-based cache,
        # used when cache_service not available)
        self._cache: Dict[Tuple[str, str], ProjectTerms] = {}
        self._trip_terms_cache: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: Optional[datetime] = None

    def get_all_project_terms(
        self, sheet_name: str = "Main terms"
    ) -> Dict[Tuple[str, str], ProjectTerms]:
        """Get all project terms from the sheet.

        Loads all project terms and caches them for future lookups.
        Uses cache if available and not expired.

        Args:
            sheet_name: Name of the sheet containing project terms

        Returns:
            Dictionary mapping (freelancer_name, project_code) to ProjectTerms

        Example:
            >>> terms_dict = reader.get_all_project_terms()
            >>> key = ("John Doe", "PROJ-001")
            >>> terms_dict[key].hourly_rate
            Decimal('85.00')
        """
        # Check if cache is valid
        if self._is_cache_valid():
            logger.debug("Using cached project terms")
            return self._cache.copy()

        # Read from sheet
        logger.info(f"Loading project terms from sheet: {sheet_name}")
        self._read_main_terms_sheet(sheet_name=sheet_name)

        return self._cache.copy()

    def get_project_terms(
        self, freelancer_name: str, project_code: str
    ) -> Optional[ProjectTerms]:
        """Get project terms for a specific freelancer and project.

        Args:
            freelancer_name: Name of the freelancer
            project_code: Project code identifier

        Returns:
            ProjectTerms if found, None otherwise

        Example:
            >>> terms = reader.get_project_terms("John Doe", "PROJ-001")
            >>> terms.hourly_rate
            Decimal('85.00')
        """
        # Ensure cache is populated
        if not self._is_cache_valid():
            self.get_all_project_terms()

        key = (freelancer_name, project_code)
        return self._cache.get(key)

    def get_trip_terms(self, sheet_name: str = "Trip Terms") -> List[Dict[str, Any]]:
        """Get trip reimbursement terms from the sheet.

        Loads trip reimbursement rules and caches them.
        Uses cache if available and not expired.

        Args:
            sheet_name: Name of the sheet containing trip terms

        Returns:
            List of dictionaries containing trip term rules

        Example:
            >>> trip_terms = reader.get_trip_terms()
            >>> trip_terms[0]['min_days']
            1
            >>> trip_terms[0]['amount_per_day']
            Decimal('50.00')
        """
        # Check if cache is valid
        if self._is_cache_valid() and self._trip_terms_cache is not None:
            logger.debug("Using cached trip terms")
            return self._trip_terms_cache.copy()

        # Read from sheet
        logger.info(f"Loading trip terms from sheet: {sheet_name}")
        self._read_trip_terms_sheet(sheet_name=sheet_name)

        return self._trip_terms_cache.copy() if self._trip_terms_cache else []

    def invalidate_cache(self):
        """Invalidate the cache, forcing a refresh on next read.

        Clears both project terms and trip terms caches.
        """
        logger.info("Invalidating project terms cache")
        self._cache = {}
        self._trip_terms_cache = None
        self._cache_timestamp = None

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid.

        Returns:
            True if cache exists and hasn't expired, False otherwise
        """
        if self._cache_timestamp is None:
            return False

        age = datetime.now() - self._cache_timestamp
        return age < timedelta(seconds=self.cache_ttl)

    def _read_main_terms_sheet(self, sheet_name: str = "Main terms"):
        """Read and parse main project terms from the sheet.

        Args:
            sheet_name: Name of the sheet to read
        """
        try:
            # Read data from sheet including headers (row 1)
            range_name = f"{sheet_name}!A1:F"

            # Use cache service if available, otherwise direct read
            if self.cache_service:
                df = self.cache_service.read_sheet_cached(
                    self.spreadsheet_id, range_name
                )
            else:
                df = self.sheets_service.read_sheet(self.spreadsheet_id, range_name)

            if df.empty:
                logger.warning(f"No project terms data found in {sheet_name}")
                self._cache = {}
                self._cache_timestamp = datetime.now()
                return

            # Parse each row
            for _, row in df.iterrows():
                terms = self._parse_main_terms_row(row.to_dict())
                if terms:
                    key = (terms.freelancer_name, terms.project_code)
                    self._cache[key] = terms

            logger.info(f"Loaded {len(self._cache)} project term entries")
            self._cache_timestamp = datetime.now()

        except Exception as e:
            logger.error(f"Failed to read project terms from {sheet_name}: {e}")
            raise

    def _read_trip_terms_sheet(self, sheet_name: str = "Trip terms"):
        """Read and parse trip reimbursement terms from the sheet.

        Args:
            sheet_name: Name of the sheet to read
        """
        try:
            # Read data from sheet including headers
            range_name = f"{sheet_name}!A1:D"

            # Use cache service if available, otherwise direct read
            if self.cache_service:
                df = self.cache_service.read_sheet_cached(
                    self.spreadsheet_id, range_name
                )
            else:
                df = self.sheets_service.read_sheet(self.spreadsheet_id, range_name)

            if df.empty:
                logger.warning(f"No trip terms data found in {sheet_name}")
                self._trip_terms_cache = []
                self._cache_timestamp = datetime.now()
                return

            # Parse each row
            trip_terms = []
            for _, row in df.iterrows():
                trip_term = self._parse_trip_terms_row(row.to_dict())
                if trip_term:
                    trip_terms.append(trip_term)

            self._trip_terms_cache = trip_terms
            logger.info(f"Loaded {len(trip_terms)} trip term entries")

            # Update cache timestamp if not already set
            if self._cache_timestamp is None:
                self._cache_timestamp = datetime.now()

        except Exception as e:
            logger.error(f"Failed to read trip terms from {sheet_name}: {e}")
            raise

    def _parse_main_terms_row(self, row: Dict[str, Any]) -> Optional[ProjectTerms]:
        """Parse a single project terms row.

        Args:
            row: Dictionary containing row data

        Returns:
            ProjectTerms object if row is valid, None if row should be skipped
        """
        try:
            # Extract and clean field values using actual column names
            freelancer_name = str(row.get("Name", "")).strip()
            project_code = str(row.get("Project", "")).strip()
            hourly_rate_str = str(row.get("Rate", "")).strip()
            cost_per_hour_str = str(row.get("Cost", "")).strip()
            travel_time_str = str(row.get("Share of travel as work", "")).strip()

            # Skip empty rows
            if not freelancer_name or not project_code:
                return None

            # Skip rows with missing required numeric values
            if not hourly_rate_str or not cost_per_hour_str:
                return None

            # Create ProjectTerms object
            # Note: travel_surcharge_percentage is not in the sheet, defaulting to 0
            terms = ProjectTerms(
                freelancer_name=freelancer_name,
                project_code=project_code,
                hourly_rate=Decimal(hourly_rate_str),
                travel_surcharge_percentage=Decimal("0"),
                travel_time_percentage=Decimal(travel_time_str)
                if travel_time_str
                else Decimal("0"),
                cost_per_hour=Decimal(cost_per_hour_str),
            )

            return terms

        except ValidationError as e:
            logger.warning(f"Validation error for project terms row: {e}")
            return None
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Error parsing project terms row for "
                f"{row.get('Freelancer', 'Unknown')}: {e}"
            )
            return None
        except Exception as e:
            logger.warning(f"Unexpected error parsing project terms row: {e}")
            return None

    def _parse_trip_terms_row(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single trip terms row.

        Args:
            row: Dictionary containing row data

        Returns:
            Dictionary with trip term data if valid, None otherwise
        """
        try:
            # Extract and clean field values
            min_days_str = str(row.get("Min Days", "")).strip()
            max_days_str = str(row.get("Max Days", "")).strip()
            reimbursement_type = str(row.get("Reimbursement Type", "")).strip()
            amount_str = str(row.get("Amount per Day", "")).strip()

            # Skip empty rows
            if not min_days_str or not max_days_str or not reimbursement_type:
                return None

            # Parse and validate
            trip_term = {
                "min_days": int(min_days_str),
                "max_days": int(max_days_str),
                "reimbursement_type": reimbursement_type,
                "amount_per_day": Decimal(amount_str),
            }

            return trip_term

        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing trip terms row: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error parsing trip terms row: {e}")
            return None
