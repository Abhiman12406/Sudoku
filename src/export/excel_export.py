"""Excel export module for allocated DeltaV signals and Technical Queries."""

import io
from pathlib import Path
from typing import BinaryIO, Optional, Sequence, Union
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.domain.models import AllocatedSignal, TechnicalQuery

ALLOCATION_COLUMNS = [
    ("Tag", "tag"),
    ("IO Type", "io_type"),
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
]

COLUMNS = ALLOCATION_COLUMNS

TQ_COLUMNS = [
    ("TQ ID", "tq_id"),
    ("Severity", "severity"),
    ("Category", "category"),
    ("Impacted Tag", "impacted_tag"),
    ("Description", "description"),
    ("Recommended Remedy", "recommended_remedy"),
]


def _auto_fit_columns(ws, min_width: int = 12) -> None:
    """Auto-fit column widths based on maximum string length in each column."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, min_width)


def export_allocation_to_excel(
    allocations: Sequence[AllocatedSignal],
    output_path_or_buffer: Optional[Union[str, Path, BinaryIO]] = None,
    tqs: Optional[Sequence[TechnicalQuery]] = None,
) -> bytes:
    """Export allocated signals to a styled Excel workbook (.xlsx).

    Args:
        allocations: Sequence of AllocatedSignal objects.
        output_path_or_buffer: Optional file path or buffer to write to.
        tqs: Optional sequence of TechnicalQuery records to write to TQ_Log sheet.

    Returns:
        Raw bytes of the generated Excel workbook.
    """
    wb = openpyxl.Workbook()

    # --- Sheet 1: Allocation ---
    ws_alloc = wb.active
    ws_alloc.title = "Allocation"

    # Header styling for Allocation
    alloc_header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    alloc_header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center")

    for col_idx, (col_name, _) in enumerate(ALLOCATION_COLUMNS, start=1):
        cell = ws_alloc.cell(row=1, column=col_idx, value=col_name)
        cell.font = alloc_header_font
        cell.fill = alloc_header_fill
        cell.alignment = center_align

    spare_font = Font(name="Calibri", size=10, italic=True, color="595959")
    spare_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    for row_idx, alloc in enumerate(allocations, start=2):
        for col_idx, (_, attr_name) in enumerate(ALLOCATION_COLUMNS, start=1):
            val = getattr(alloc, attr_name)
            if hasattr(val, "value"):
                val = val.value
            cell = ws_alloc.cell(row=row_idx, column=col_idx, value=val)

            if alloc.is_spare:
                cell.font = spare_font
                cell.fill = spare_fill

            if attr_name in ("cioc", "baseplate", "slot", "pair_no", "io_type"):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = left_align


    _auto_fit_columns(ws_alloc, min_width=12)
    ws_alloc.freeze_panes = "A2"

    # --- Sheet 2: TQ_Log ---
    ws_tq = wb.create_sheet(title="TQ_Log")

    tq_header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    tq_header_fill = PatternFill(start_color="800000", end_color="800000", fill_type="solid")

    for col_idx, (col_name, _) in enumerate(TQ_COLUMNS, start=1):
        cell = ws_tq.cell(row=1, column=col_idx, value=col_name)
        cell.font = tq_header_font
        cell.fill = tq_header_fill
        cell.alignment = center_align

    if tqs:
        for row_idx, tq in enumerate(tqs, start=2):
            for col_idx, (_, attr_name) in enumerate(TQ_COLUMNS, start=1):
                val = getattr(tq, attr_name)
                if hasattr(val, "value"):
                    val = val.value
                cell = ws_tq.cell(row=row_idx, column=col_idx, value=val)

                if attr_name in ("tq_id", "severity"):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = left_align

    _auto_fit_columns(ws_tq, min_width=14)
    ws_tq.freeze_panes = "A2"

    # Save workbook to memory buffer
    buf = io.BytesIO()
    wb.save(buf)
    excel_bytes = buf.getvalue()

    if output_path_or_buffer is not None:
        if isinstance(output_path_or_buffer, (str, Path)):
            with open(output_path_or_buffer, "wb") as f:
                f.write(excel_bytes)
        elif hasattr(output_path_or_buffer, "write"):
            output_path_or_buffer.write(excel_bytes)

    return excel_bytes
