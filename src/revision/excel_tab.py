"""Excel generator for Revision_Impact worksheet."""

from typing import Dict, List, Optional, Sequence
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.domain.models import AllocatedSignal
from src.revision.classifier import DiffStatus, SignalDiffItem
from src.revision.solver import RevisionAllocationResult


def _auto_fit_columns(ws, min_width: int = 12) -> None:
    """Auto-fit column widths based on cell string lengths."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, min_width)


def populate_revision_impact_sheet(
    ws,
    revision_result: RevisionAllocationResult,
    rev_a_allocations: Sequence[AllocatedSignal],
) -> None:
    """Populate and format the Revision_Impact summary and detailed diff worksheet.

    Args:
        ws: openpyxl Worksheet object.
        revision_result: Result object from solve_revision_allocation.
        rev_a_allocations: Sequence of Rev A baseline allocations.
    """
    ws.views.sheetView[0].showGridLines = True

    # Styling constants
    font_title = Font(name="Calibri", size=16, bold=True, color="1F497D")
    font_section = Font(name="Calibri", size=12, bold=True, color="1F497D")
    font_kpi_label = Font(name="Calibri", size=10, bold=True, color="595959")
    font_kpi_val = Font(name="Calibri", size=12, bold=True, color="000000")
    font_table_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, color="000000")

    fill_table_hdr = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    fill_kpi_bg = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")

    fill_added = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    font_added = Font(name="Calibri", size=10, bold=True, color="276A3C")

    fill_deleted = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    font_deleted = Font(name="Calibri", size=10, bold=True, color="C00000")

    fill_moved = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    font_moved = Font(name="Calibri", size=10, bold=True, color="B25900")

    fill_unchanged = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    font_unchanged = Font(name="Calibri", size=10, color="595959")

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    # 1. Sheet Title
    ws.cell(row=1, column=1, value="Revision Impact Summary & Perturbation Audit Matrix").font = font_title
    ws.cell(
        row=2,
        column=1,
        value="Emerson DeltaV Electronic Marshalling • Automated Churn Minimization (Rev A vs Rev B)",
    ).font = Font(name="Calibri", size=10, italic=True, color="595959")

    # 2. KPI Summary Block (Rows 4-10)
    ws.cell(row=4, column=1, value="Executive Revision Metrics").font = font_section

    diff = revision_result.diff_result
    kpis = [
        ("Total Baseline Rev A Signals", diff.total_rev_a),
        ("Total New Rev B Signals", diff.total_rev_b),
        ("Unchanged Loops (Frozen, Δ=0)", len(diff.unchanged)),
        ("Modified Loops", len(diff.modified)),
        ("Added Loops (Green)", len(diff.added)),
        ("Deleted Loops (Red)", len(diff.deleted)),
        ("Relocated Loops (Orange)", len(revision_result.moved_signals)),
        ("Vacated Slots Backfilled", len(revision_result.backfilled_slots)),
        ("Total Movement Penalty Score (min Δ)", revision_result.perturbation_score),
    ]

    for idx, (label, val) in enumerate(kpis):
        r = 5 + idx // 3
        c = 1 + (idx % 3) * 3

        cell_lbl = ws.cell(row=r, column=c, value=label)
        cell_lbl.font = font_kpi_label
        cell_lbl.fill = fill_kpi_bg
        cell_lbl.border = thin_border
        cell_lbl.alignment = align_left

        cell_val = ws.cell(row=r, column=c + 1, value=val)
        cell_val.font = font_kpi_val
        cell_val.fill = fill_kpi_bg
        cell_val.border = thin_border
        cell_val.alignment = align_center

    # 3. Detailed Changes Table (Rows 10+)
    start_row = 10
    ws.cell(row=start_row, column=1, value="Detailed Loop Revision Log").font = font_section

    table_headers = [
        "Tag",
        "Revision Status",
        "Rev A Location",
        "Rev B Location",
        "Movement Displacement",
        "Perturbation Penalty (Δ)",
        "IO Type",
        "Cable ID",
        "Pair No",
        "Segregation",
        "Engineering Change Notes",
    ]

    hdr_row = start_row + 1
    for col_idx, h_text in enumerate(table_headers, start=1):
        cell = ws.cell(row=hdr_row, column=col_idx, value=h_text)
        cell.font = font_table_hdr
        cell.fill = fill_table_hdr
        cell.alignment = align_center
        cell.border = thin_border

    # Maps for coordinate resolution
    rev_a_by_tag: Dict[str, AllocatedSignal] = {a.tag: a for a in rev_a_allocations if a.tag}
    rev_b_by_tag: Dict[str, AllocatedSignal] = {a.tag: a for a in revision_result.allocations if a.tag}

    curr_row = hdr_row + 1

    for item in diff.items:
        orig = rev_a_by_tag.get(item.tag)
        alloc = rev_b_by_tag.get(item.tag)

        # Coordinate strings
        if orig:
            loc_a = f"{orig.cabinet_name} / {orig.cioc_name} / {orig.baseplate_name} / {orig.slot_name}"
        else:
            loc_a = "-"

        if alloc:
            loc_b = f"{alloc.cabinet_name} / {alloc.cioc_name} / {alloc.baseplate_name} / {alloc.slot_name}"
        else:
            loc_b = "-"

        # Movement type & delta
        delta = 0
        if item.status == DiffStatus.DELETED:
            movement_type = "DELETED (Slot Vacated)"
            row_fill = fill_deleted
            row_font = font_deleted
        elif item.status == DiffStatus.ADDED:
            movement_type = "NEW ALLOCATION"
            row_fill = fill_added
            row_font = font_added
        elif item.status == DiffStatus.UNCHANGED:
            movement_type = "STATIONARY (Frozen)"
            row_fill = fill_unchanged
            row_font = font_unchanged
        else:
            # MODIFIED
            if orig and alloc:
                d_cab = 1 if alloc.cabinet_id != orig.cabinet_id else 0
                d_cioc = 1 if alloc.cioc != orig.cioc else 0
                d_bp = 1 if alloc.baseplate != orig.baseplate else 0
                d_slot = 1 if alloc.slot != orig.slot else 0
                delta = 10000 * d_cab + 1000 * d_cioc + 100 * d_bp + 10 * d_slot

                if delta == 0:
                    movement_type = "STATIONARY (Modified in Place)"
                    row_fill = fill_unchanged
                    row_font = font_unchanged
                elif d_cab:
                    movement_type = "CABINET SHIFT"
                    row_fill = fill_moved
                    row_font = font_moved
                elif d_cioc:
                    movement_type = "CIOC SHIFT"
                    row_fill = fill_moved
                    row_font = font_moved
                elif d_bp:
                    movement_type = "BASEPLATE SHIFT"
                    row_fill = fill_moved
                    row_font = font_moved
                else:
                    movement_type = "SLOT SHIFT"
                    row_fill = fill_moved
                    row_font = font_moved
            else:
                movement_type = "MODIFIED"
                row_fill = fill_moved
                row_font = font_moved

        # Data values
        target_sig = alloc or orig or item.rev_b_signal or item.rev_a_signal
        if target_sig is not None:
            io_val = target_sig.io_type.value if hasattr(target_sig.io_type, "value") else str(target_sig.io_type)
            cbl_val = target_sig.cable_id or "-"
            pair_val = str(target_sig.pair_no) if target_sig.pair_no is not None else "-"
            seg_val = target_sig.segregation or "Common"
        else:
            io_val = "-"
            cbl_val = "-"
            pair_val = "-"
            seg_val = "-"
        notes = "; ".join(item.changes) if item.changes else "Unchanged"

        values = [
            item.tag,
            item.status.value,
            loc_a,
            loc_b,
            movement_type,
            delta,
            io_val,
            cbl_val,
            pair_val,
            seg_val,
            notes,
        ]

        for col_idx, cell_val_data in enumerate(values, start=1):
            c_cell = ws.cell(row=curr_row, column=col_idx, value=cell_val_data)
            c_cell.font = row_font if col_idx in (1, 2, 5) else font_data
            c_cell.fill = row_fill if col_idx in (1, 2, 5) else PatternFill(fill_type=None)
            c_cell.border = thin_border
            if col_idx in (2, 5, 6, 7, 9, 10):
                c_cell.alignment = align_center
            else:
                c_cell.alignment = align_left

        curr_row += 1

    _auto_fit_columns(ws, min_width=14)
