"""
Google Sheets service with modern authentication and retry handling.
"""

import logging
from typing import Any, Dict, List, Optional

import google.auth
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.services.retry_handler import RetryHandler

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """
    Google Sheets service with flexible authentication and retry handling.

    Features:
    - Service account credentials (from .env) or Application Default Credentials (ADC)
    - Automatic retry with exponential backoff
    - Batch operations for efficiency
    - Pandas DataFrame integration
    - Comprehensive error handling
    """

    def __init__(
        self,
        credentials: Optional[Dict[str, Any]] = None,
        retry_handler: Optional[RetryHandler] = None,
        scopes: Optional[List[str]] = None,
    ):
        """
        Initialize Google Sheets service with direct service account access.

        Args:
            credentials: Service account credentials dict from
                        config.get_google_service_account_info().
                        If None, falls back to ADC (Application Default Credentials)
            retry_handler: Custom retry handler instance
            scopes: Custom OAuth scopes for authentication

        Note:
            Service account must have direct access to spreadsheets via
            Shared Drive or direct file sharing.
        """
        self.credentials_info = credentials
        self.retry_handler = retry_handler or RetryHandler()
        self.scopes = scopes or [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # Initialize Google Sheets API client
        self._service = self._create_service()

    def _create_service(self):
        """
        Create Google Sheets API service using direct service account access or ADC.

        Returns:
            Google Sheets API service instance
        """
        try:
            if self.credentials_info:
                # Use service account credentials with direct access
                credentials = service_account.Credentials.from_service_account_info(
                    self.credentials_info, scopes=self.scopes
                )
                project = self.credentials_info.get("project_id", "unknown")
                logger.info(
                    f"Google Sheets service initialized with service account "
                    f"for project: {project}"
                )
            else:
                # Fall back to Application Default Credentials (ADC)
                credentials, project = google.auth.default(scopes=self.scopes)
                logger.info(
                    f"Google Sheets service initialized with ADC for project: {project}"
                )

            service = build("sheets", "v4", credentials=credentials)
            return service

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            raise

    def read_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        value_render_option: str = "UNFORMATTED_VALUE",
    ) -> pd.DataFrame:
        """
        Read data from a Google Sheet and return as pandas DataFrame.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range to read
            value_render_option: How values should be rendered

        Returns:
            pandas DataFrame with the sheet data

        Raises:
            HttpError: If API request fails
        """

        def _read_operation():
            return (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueRenderOption=value_render_option,
                )
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_read_operation)
            values = result.get("values", [])

            if not values:
                logger.info(f"No data found in range {range_name}")
                return pd.DataFrame()

            # Convert to DataFrame with first row as headers
            if len(values) > 1:
                headers = values[0]
                data = values[1:]

                # Ensure all rows have the same number of columns
                max_cols = len(headers)
                data = [row + [""] * (max_cols - len(row)) for row in data]

                df = pd.DataFrame(data, columns=headers)
            else:
                # Only one row - treat as data without headers
                df = pd.DataFrame(values)

            logger.debug(f"Read {len(df)} rows from {range_name}")
            return df

        except HttpError as e:
            logger.error(f"Failed to read sheet {spreadsheet_id}:{range_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error reading sheet: {e}")
            raise

    def write_sheet(
        self,
        spreadsheet_id: str,
        range_name: str,
        data: pd.DataFrame,
        include_headers: bool = False,
        value_input_option: str = "RAW",
    ) -> Dict[str, Any]:
        """
        Write pandas DataFrame to a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range to write to
            data: pandas DataFrame to write
            include_headers: Whether to include column headers
            value_input_option: How input data should be interpreted

        Returns:
            Response from the API call

        Raises:
            HttpError: If API request fails
        """
        # Prepare data for API
        values = []

        if include_headers:
            values.append(data.columns.tolist())

        # Convert DataFrame to list of lists
        for _, row in data.iterrows():
            values.append(row.astype(str).tolist())

        def _write_operation():
            return (
                self._service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body={"values": values},
                )
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_write_operation)

            logger.info(
                f"Wrote {len(values)} rows to {spreadsheet_id}:{range_name}. "
                f"Updated {result.get('updatedCells', 0)} cells"
            )
            return result

        except HttpError as e:
            logger.error(f"Failed to write to sheet {spreadsheet_id}:{range_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error writing to sheet: {e}")
            raise

    def batch_read_sheets(
        self,
        spreadsheet_id: str,
        ranges: List[str],
        value_render_option: str = "UNFORMATTED_VALUE",
    ) -> List[pd.DataFrame]:
        """
        Read multiple ranges from a spreadsheet in a single API call.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            ranges: List of A1 notation ranges to read
            value_render_option: How values should be rendered

        Returns:
            List of pandas DataFrames, one for each range

        Raises:
            HttpError: If API request fails
        """

        def _batch_read_operation():
            return (
                self._service.spreadsheets()
                .values()
                .batchGet(
                    spreadsheetId=spreadsheet_id,
                    ranges=ranges,
                    valueRenderOption=value_render_option,
                )
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_batch_read_operation)
            value_ranges = result.get("valueRanges", [])

            dataframes = []
            for i, value_range in enumerate(value_ranges):
                values = value_range.get("values", [])

                if not values:
                    dataframes.append(pd.DataFrame())
                    continue

                # Convert to DataFrame
                if len(values) > 1:
                    headers = values[0]
                    data = values[1:]

                    # Ensure consistent column count
                    max_cols = len(headers)
                    data = [row + [""] * (max_cols - len(row)) for row in data]

                    df = pd.DataFrame(data, columns=headers)
                else:
                    df = pd.DataFrame(values)

                dataframes.append(df)

            logger.info(f"Batch read {len(ranges)} ranges from {spreadsheet_id}")
            return dataframes

        except HttpError as e:
            logger.error(f"Failed to batch read from {spreadsheet_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in batch read: {e}")
            raise

    def get_sheet_metadata(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get metadata about a spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet

        Returns:
            Spreadsheet metadata

        Raises:
            HttpError: If API request fails
        """

        def _metadata_operation():
            return (
                self._service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_metadata_operation)

            logger.debug(f"Retrieved metadata for spreadsheet {spreadsheet_id}")
            return result

        except HttpError as e:
            logger.error(f"Failed to get metadata for {spreadsheet_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting metadata: {e}")
            raise

    def clear_sheet_range(self, spreadsheet_id: str, range_name: str) -> Dict[str, Any]:
        """
        Clear a range in a spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range to clear

        Returns:
            Response from the API call

        Raises:
            HttpError: If API request fails
        """

        def _clear_operation():
            return (
                self._service.spreadsheets()
                .values()
                .clear(spreadsheetId=spreadsheet_id, range=range_name, body={})
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_clear_operation)

            logger.info(f"Cleared range {range_name} in {spreadsheet_id}")
            return result

        except HttpError as e:
            logger.error(f"Failed to clear range {range_name} in {spreadsheet_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error clearing range: {e}")
            raise

    def create_sheet(
        self,
        spreadsheet_id: str,
        sheet_title: str,
        row_count: int = 1000,
        column_count: int = 26,
    ) -> Dict[str, Any]:
        """
        Create a new sheet in an existing spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            sheet_title: Title for the new sheet
            row_count: Number of rows in the new sheet
            column_count: Number of columns in the new sheet

        Returns:
            Response from the API call

        Raises:
            HttpError: If API request fails
        """

        def _create_operation():
            requests = [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_title,
                            "gridProperties": {
                                "rowCount": row_count,
                                "columnCount": column_count,
                            },
                        }
                    }
                }
            ]

            return (
                self._service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_create_operation)

            logger.info(f"Created sheet '{sheet_title}' in {spreadsheet_id}")
            return result

        except HttpError as e:
            logger.error(
                f"Failed to create sheet '{sheet_title}' in {spreadsheet_id}: {e}"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating sheet: {e}")
            raise

    def append_data(
        self,
        spreadsheet_id: str,
        range_name: str,
        data: pd.DataFrame,
        value_input_option: str = "RAW",
    ) -> Dict[str, Any]:
        """
        Append data to the end of a sheet range.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation range to append to
            data: pandas DataFrame to append
            value_input_option: How input data should be interpreted

        Returns:
            Response from the API call

        Raises:
            HttpError: If API request fails
        """
        # Convert DataFrame to list of lists
        values = []
        for _, row in data.iterrows():
            values.append(row.astype(str).tolist())

        def _append_operation():
            return (
                self._service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    insertDataOption="INSERT_ROWS",
                    body={"values": values},
                )
                .execute()
            )

        try:
            result = self.retry_handler.execute_with_retry(_append_operation)

            logger.info(f"Appended {len(values)} rows to {spreadsheet_id}:{range_name}")
            return result

        except HttpError as e:
            logger.error(f"Failed to append to {spreadsheet_id}:{range_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error appending data: {e}")
            raise
