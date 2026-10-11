"""Template-preserving Excel overlay cloner for DeltaV allocation deliverables."""

import copy
import io
from pathlib import Path
import re
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Sequence, Union

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.domain.models import AllocatedSignal


# Field value extractors via clean dictionary dispatch
FIELD_EXTRACTORS: Dict[str, Callable[[AllocatedSignal], Any]] = {
    "tag": lambda a: a.tag,
    "io_type": lambda a: a.io_type.value if hasattr(a.io_type, "value") else str(a.io_type),
    "cabinet": lambda a: a.cabinet_name,
    "cioc": lambda a: a.cioc,
    "baseplate": lambda a: a.baseplate,
    "slot": lambda a: a.slot,
    "cable_id": lambda a: a.cable_id or "-",
    "pair_no": lambda a: a.pair_no or "-",
    "charm_model": lambda a: a.charm_model or "-",
    "charm_part_no": lambda a: a.charm_part_no or "-",
    "terminal_block_type": lambda a: a.terminal_block_type or "-",
    "terminal_block_part_no": lambda a: a.terminal_block_part_no or "-",
    "description": lambda a: a.description or "",
    "segregation": lambda a: a.segregation or "-",
    "status": lambda a: "WIRED SPARE" if a.is_spare else "Active Loop",
}

# Normalized header synonyms for auto-mapping
HEADER_SYNONYMS: Dict[str, List[str]] = {
    "tag": ["tag", "instrument tag", "loop tag", "tag no", "tagname", "loop_tag", "instrument_tag"],
    "io_type": ["io type", "signal type", "channel type", "io", "type", "io_type", "signal_type"],
    "cabinet": ["cabinet", "cab", "cabinet id", "cab id", "enclosure", "cabinet_id"],
    "cioc": ["cioc", "cioc id", "carrier", "cioc no", "cioc_id", "carrier_id"],
    "baseplate": ["baseplate", "bp", "base plate", "carrier slot", "baseplate_no", "bp_no"],
    "slot": ["slot", "channel", "charm slot", "ch", "slot_no", "channel_no"],
    "cable_id": ["cable id", "cable no", "cable", "trunk cable", "multicore", "cable_no"],
    "pair_no": ["pair no", "pair", "pair number", "wire pair", "pair_id", "pair_no"],
    "charm_model": ["charm model", "charm", "charm type", "io card", "charm_model"],
    "charm_part_no": ["charm part no", "charm p/n", "charm part", "part no", "charm part number", "charm_part_no"],
    "terminal_block_type": ["terminal block type", "tb type", "terminal block", "tb", "terminal_block_type"],
    "terminal_block_part_no": ["terminal block part no", "tb part no", "tb p/n", "terminal_block_part_no"],
    "description": ["description", "desc", "service", "tag description", "loop description"],
    "segregation": ["segregation", "seg", "train", "redundancy"],
    "status": ["status", "signal status", "allocation status", "rev status", "channel status", "spare"],
}


def _normalize_header(text: str) -> str:
    """Normalize text by lowercasing and stripping punctuation/whitespace."""
    return re.sub(r"[\s_\-]+", " ", str(text).strip().lower())


def _find_field_for_header(header_text: str) -> Optional[str]:
    """Match header text to known field using exact synonym match or token match."""
    norm = _normalize_header(header_text)
    if not norm:
        return None

    # 1. Exact match
    for field, synonyms in HEADER_SYNONYMS.items():
        for syn in synonyms:
            if norm == syn:
                return field

    # 2. Token set containment for multi-word phrases (avoids short substring false positives)
    norm_tokens = set(norm.split())
    for field, synonyms in HEADER_SYNONYMS.items():
        for syn in synonyms:
            syn_tokens = set(syn.split())
            if len(syn_tokens) > 1 and syn_tokens.issubset(norm_tokens):
                return field

    return None


def _adjust_formula_row(formula: str, source_row: int, target_row: int) -> str:
    """Adjust row numbers in an Excel formula from source_row to target_row."""
    if not formula.startswith("="):
        return formula

    pattern = rf"([A-Za-z]+){source_row}\b"
    replacement = rf"\g<1>{target_row}"
    return re.sub(pattern, replacement, formula)


def overlay_allocation_on_template(
    template_path_or_bytes: Union[str, Path, BinaryIO, bytes],
    allocations: Sequence[AllocatedSignal],
    sheet_name: Optional[str] = None,
) -> openpyxl.Workbook:
    """Inject allocated signals into a customer Excel template preserving styles and formulas.

    Args:
        template_path_or_bytes: Blank customer template workbook (.xlsx).
        allocations: Sequence of AllocatedSignal objects.
        sheet_name: Optional name of the worksheet to overlay data onto.

    Returns:
        openpyxl.Workbook with data injected and formatting intact.
    """
    if isinstance(template_path_or_bytes, bytes):
        buffer = io.BytesIO(template_path_or_bytes)
    elif isinstance(template_path_or_bytes, (str, Path)):
        buffer = open(template_path_or_bytes, "rb")
    else:
        buffer = template_path_or_bytes

    wb = openpyxl.load_workbook(buffer, data_only=False)

    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    # 1. Map columns in row 1
    max_col = ws.max_column
    col_to_field: Dict[int, str] = {}
    formula_cols: Dict[int, str] = {}
    sample_styles: Dict[int, openpyxl.cell.cell.Cell] = {}

    for c in range(1, max_col + 1):
        h_val = ws.cell(row=1, column=c).value
        if h_val:
            field = _find_field_for_header(str(h_val))
            if field:
                col_to_field[c] = field

        # Check row 2 for existing formatting and formulas
        cell_r2 = ws.cell(row=2, column=c)
        sample_styles[c] = cell_r2
        val_r2 = cell_r2.value
        if isinstance(val_r2, str) and val_r2.startswith("="):
            formula_cols[c] = val_r2

    # If row 1 was completely blank, write default headers
    if not col_to_field:
        default_headers = [
            ("Tag", "tag"),
            ("IO Type", "io_type"),
            ("Cabinet", "cabinet"),
            ("CIOC", "cioc"),
            ("Baseplate", "baseplate"),
            ("Slot", "slot"),
            ("Cable ID", "cable_id"),
            ("Pair No", "pair_no"),
            ("CHARM Model", "charm_model"),
            ("CHARM Part No", "charm_part_no"),
            ("Terminal Block Type", "terminal_block_type"),
            ("Terminal Block Part No", "terminal_block_part_no"),
            ("Description", "description"),
            ("Segregation", "segregation"),
            ("Status", "status"),
        ]
        hdr_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        hdr_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        for c_idx, (h_name, f_key) in enumerate(default_headers, start=1):
            cell = ws.cell(row=1, column=c_idx, value=h_name)
            cell.font = hdr_font
            cell.fill = hdr_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            col_to_field[c_idx] = f_key
        max_col = len(default_headers)

    # 2. Inject allocated loop records into exact column coordinates starting at data row 2
    for idx, alloc in enumerate(allocations):
        row_num = 2 + idx

        # First, apply template styling and replicate formulas
        for c in range(1, max(max_col + 1, ws.max_column + 1)):
            target_cell = ws.cell(row=row_num, column=c)
            ref_cell = sample_styles.get(c)

            if ref_cell and ref_cell.has_style:
                if ref_cell.font:
                    target_cell.font = copy.copy(ref_cell.font)
                if ref_cell.fill:
                    target_cell.fill = copy.copy(ref_cell.fill)
                if ref_cell.border:
                    target_cell.border = copy.copy(ref_cell.border)
                if ref_cell.alignment:
                    target_cell.alignment = copy.copy(ref_cell.alignment)
                if ref_cell.number_format:
                    target_cell.number_format = ref_cell.number_format
                if ref_cell.protection:
                    target_cell.protection = copy.copy(ref_cell.protection)

            # Replicate formula if this column contains a formula
            if c in formula_cols:
                target_cell.value = _adjust_formula_row(formula_cols[c], source_row=2, target_row=row_num)

        # Write mapped data values using extractor dispatch table
        for c, field in col_to_field.items():
            extractor = FIELD_EXTRACTORS.get(field)
            if extractor:
                ws.cell(row=row_num, column=c, value=extractor(alloc))

    return wb
