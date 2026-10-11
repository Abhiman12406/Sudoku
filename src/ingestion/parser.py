"""Ingestion parser for instrument signal spreadsheets."""

from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.domain.models import IOType, Signal, TechnicalQuery
from src.ingestion.mapper import auto_map_columns
from src.ingestion.validator import validate_dataframe


def _read_dataframe(file_or_path: Union[str, Path, BinaryIO]) -> pd.DataFrame:
    """Read Excel or CSV file into a pandas DataFrame."""
    if isinstance(file_or_path, (str, Path)):
        path_str = str(file_or_path).lower()
        if path_str.endswith(".csv"):
            df = pd.read_csv(file_or_path)
        else:
            df = pd.read_excel(file_or_path, engine="openpyxl")
    else:
        # Buffer: try Excel first, fall back to CSV if needed
        try:
            df = pd.read_excel(file_or_path, engine="openpyxl")
        except Exception:
            if hasattr(file_or_path, "seek"):
                file_or_path.seek(0)
            df = pd.read_csv(file_or_path)

    # Drop fully empty rows
    df = df.dropna(how="all")
    return df


def parse_and_validate_signals(
    file_or_path: Union[str, Path, BinaryIO],
) -> Tuple[List[Signal], List[TechnicalQuery]]:
    """Parse an Excel or CSV file, validate rows, isolate invalid rows, and generate TQs.

    Args:
        file_or_path: File path or file-like binary buffer.

    Returns:
        Tuple of (list of valid Signal models, list of generated TechnicalQuery records).
    """
    df = _read_dataframe(file_or_path)
    if df.empty:
        return [], []

    col_map = auto_map_columns(list(df.columns))
    return validate_dataframe(df, col_map=col_map)


def parse_signal_file(
    file_or_path: Union[str, Path, BinaryIO],
    isolate_tqs: bool = False,
) -> List[Signal]:
    """Parse an Excel or CSV file into a list of validated Signal domain models.

    Args:
        file_or_path: File path or file-like binary buffer.
        isolate_tqs: If True, invalid rows are quarantined into TQs without raising an error.
                     If False (default), raises ValueError on critical validation errors for
                     strict backwards compatibility.

    Returns:
        List of validated Signal models.
    """
    valid_signals, tqs = parse_and_validate_signals(file_or_path)

    if not isolate_tqs and tqs:
        critical_tqs = [t for t in tqs if t.severity.value == "Critical"]
        if critical_tqs:
            raise ValueError(critical_tqs[0].description)

    return valid_signals
