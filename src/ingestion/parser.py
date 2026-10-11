"""Ingestion parser for instrument signal spreadsheets."""

from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Union
import pandas as pd

from src.domain.models import IOType, Signal

COLUMN_SYNONYMS: Dict[str, List[str]] = {
    "tag": ["tag", "instrument_tag", "tag_no", "tagname", "loop_tag"],
    "io_type": ["io_type", "signal_type", "type", "io", "channel_type"],
    "cable_id": ["cable_id", "cable_no", "cable", "trunk_cable", "multicore"],
    "pair_no": ["pair_no", "pair", "pair_number", "wire_pair", "pair_id"],
    "description": ["description", "desc", "service", "tag_desc", "instrument_description"],
    "io_group": ["io_group", "group", "grp", "unit", "area", "system"],
    "segregation": ["segregation", "seg", "train", "redundancy", "channel_seg"],
}


def _normalize_col_name(col: str) -> str:
    return str(col).strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_column_mapping(columns: List[str]) -> Dict[str, str]:
    """Map detected raw columns to standard Signal field names."""
    normalized = {_normalize_col_name(c): c for c in columns}
    mapping: Dict[str, str] = {}

    for field, synonyms in COLUMN_SYNONYMS.items():
        for syn in synonyms:
            syn_norm = _normalize_col_name(syn)
            if syn_norm in normalized:
                mapping[field] = normalized[syn_norm]
                break

    if "tag" not in mapping:
        raise ValueError("Missing required column for 'Tag' in signal file.")
    if "io_type" not in mapping:
        raise ValueError("Missing required column for 'IO Type' in signal file.")

    return mapping


def parse_signal_file(file_or_path: Union[str, Path, BinaryIO]) -> List[Signal]:
    """Parse an Excel or CSV file into a list of validated Signal domain models.

    Args:
        file_or_path: File path or file-like binary buffer.

    Returns:
        List of validated Signal models.
    """
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
    if df.empty:
        return []

    col_map = _resolve_column_mapping(list(df.columns))

    signals: List[Signal] = []
    for idx, row in df.iterrows():
        raw_tag = row.get(col_map["tag"])
        raw_io = row.get(col_map["io_type"])

        if pd.isna(raw_tag) or str(raw_tag).strip() == "":
            continue
        if pd.isna(raw_io) or str(raw_io).strip() == "":
            raise ValueError(f"Row {idx + 1}: Missing IO Type for tag '{raw_tag}'")

        cable_val = row.get(col_map.get("cable_id")) if "cable_id" in col_map else None
        pair_val = row.get(col_map.get("pair_no")) if "pair_no" in col_map else None
        desc_val = row.get(col_map.get("description")) if "description" in col_map else None
        grp_val = row.get(col_map.get("io_group")) if "io_group" in col_map else None
        seg_val = row.get(col_map.get("segregation")) if "segregation" in col_map else None

        cable_id = str(cable_val).strip() if pd.notna(cable_val) and str(cable_val).strip() != "" else None
        pair_no = int(pair_val) if pd.notna(pair_val) and str(pair_val).strip() != "" else None
        description = str(desc_val).strip() if pd.notna(desc_val) else None
        io_group = str(grp_val).strip() if pd.notna(grp_val) else None
        segregation = str(seg_val).strip().upper() if pd.notna(seg_val) else None

        # Normalize IO type string
        io_type_str = str(raw_io).strip().upper()

        signals.append(
            Signal(
                tag=str(raw_tag).strip(),
                io_type=IOType(io_type_str),
                cable_id=cable_id,
                pair_no=pair_no,
                description=description,
                io_group=io_group,
                segregation=segregation,
            )
        )

    return signals
