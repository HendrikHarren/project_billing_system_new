"""Output formatting utilities for CLI."""

from typing import List

import click


def format_success(message: str) -> str:
    """Format a success message with green color.

    Args:
        message: The success message to format

    Returns:
        Formatted success message with color
    """
    return click.style(f"✓ {message}", fg="green", bold=True)


def format_error(message: str) -> str:
    """Format an error message with red color.

    Args:
        message: The error message to format

    Returns:
        Formatted error message with color
    """
    return click.style(f"✗ {message}", fg="red", bold=True)


def format_warning(message: str) -> str:
    """Format a warning message with yellow color.

    Args:
        message: The warning message to format

    Returns:
        Formatted warning message with color
    """
    return click.style(f"⚠ {message}", fg="yellow", bold=True)


def format_info(message: str) -> str:
    """Format an info message with blue color.

    Args:
        message: The info message to format

    Returns:
        Formatted info message with color
    """
    return click.style(f"ℹ {message}", fg="blue")


def format_table(headers: List[str], rows: List[List[str]], max_width: int = 80) -> str:
    """Format data as a table.

    Args:
        headers: List of column headers
        rows: List of data rows (each row is a list of cell values)
        max_width: Maximum width for each column (default: 80)

    Returns:
        Formatted table as a string
    """
    if not headers:
        return ""

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Limit column widths to max_width
    col_widths = [min(w, max_width) for w in col_widths]

    # Create separator line
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    # Format header row
    header_row = (
        "|"
        + "|".join(
            f" {h:<{col_widths[i]}} "
            for i, h in enumerate(headers)
            if i < len(col_widths)
        )
        + "|"
    )

    # Format data rows
    data_rows = []
    for row in rows:
        formatted_cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cell_str = str(cell)[: col_widths[i]]  # Truncate if needed
                formatted_cells.append(f" {cell_str:<{col_widths[i]}} ")
        data_rows.append("|" + "|".join(formatted_cells) + "|")

    # Assemble table
    table_lines = [separator, header_row, separator]
    if rows:
        table_lines.extend(data_rows)
        table_lines.append(separator)

    return "\n".join(table_lines)
