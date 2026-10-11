"""Excel export module for 5-tab DeltaV engineering deliverable packages."""

import io
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Sequence, Union
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.domain.models import AllocatedSignal, SegregationPolicy, TechnicalQuery
from src.export.audit_report import generate_rule_compliance_audit
from src.export.metrics import compute_cabinet_summary
from src.export.template_overlay import overlay_allocation_on_template

ALLOCATION_COLUMNS = [
    ("Tag", "tag"),
    ("IO Type", "io_type"),
    ("Cabinet", "cabinet_name"),
    ("CIOC", "cioc"),
    ("Baseplate", "baseplate"),
    ("Slot", "slot"),
    ("Cable ID", "cable_id"),
    ("Pair No", "pair_no"),
    ("CHARM Model", "charm_model"),
    ("CHARM Part No", "charm_part_no"),
    ("Terminal Block Type", "terminal_block_type"),
    ("Terminal Block Part No", "terminal_block_part_no"),
    ("Segregation", "segregation"),
    ("Description", "description"),
    ("Status", "status"),
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

CABINET_SUMMARY_COLUMNS = [
    ("Cabinet ID", "cabinet_id"),
    ("Active CIOCs", "ciocs_list"),
    ("Total Capacity", "total_capacity"),
    ("Active Loops", "active_loops"),
    ("Wired Spares", "wired_spares"),
    ("Total Allocated", "total_allocated"),
    ("Free Spares", "free_spares"),
    ("Utilization %", "utilization_str"),
]

RULE_COMPLIANCE_COLUMNS = [
    ("Rule ID", "rule_id"),
    ("Rule Name", "rule_name"),
    ("Category", "category"),
    ("Requirement", "requirement"),
    ("Tested Count", "tested_count"),
    ("Violations", "violations"),
    ("Status", "status"),
    ("Remarks", "remarks"),
]


def _auto_fit_columns(ws, min_width: int = 12) -> None:
    """Auto-fit column widths based on maximum string length sampled across up to 100 rows."""
    max_rows = min(ws.max_row, 100)
    for col_idx in range(1, ws.max_column + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for r in range(1, max_rows + 1):
            val_str = str(ws.cell(row=r, column=col_idx).value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, min_width)


def _populate_allocation_sheet(ws, allocations: Sequence[AllocatedSignal]) -> None:
    """Populate and format the Allocation worksheet with high-throughput batching."""
    alloc_header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    alloc_header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    for col_idx, (col_name, _) in enumerate(ALLOCATION_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = alloc_header_font
        cell.fill = alloc_header_fill
        cell.alignment = center_align

    spare_font = Font(name="Calibri", size=10, italic=True, color="595959")
    spare_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    train_a_font = Font(name="Calibri", size=10, color="002060", bold=True)
    train_b_font = Font(name="Calibri", size=10, color="B25900", bold=True)

    center_cols = {
        col_idx
        for col_idx, (_, attr_name) in enumerate(ALLOCATION_COLUMNS, start=1)
        if attr_name in ("cioc", "baseplate", "slot", "pair_no", "io_type", "segregation", "cabinet_name", "status")
    }
    seg_col_idx = next(col_idx for col_idx, (_, attr_name) in enumerate(ALLOCATION_COLUMNS, start=1) if attr_name == "segregation")
    status_col_idx = next(col_idx for col_idx, (_, attr_name) in enumerate(ALLOCATION_COLUMNS, start=1) if attr_name == "status")

    for alloc in allocations:
        row_vals = []
        is_spare = alloc.is_spare
        for _, attr_name in ALLOCATION_COLUMNS:
            if attr_name == "status":
                val = "WIRED SPARE" if is_spare else "Active Loop"
            else:
                val = getattr(alloc, attr_name)
                if hasattr(val, "value"):
                    val = val.value
            row_vals.append(val)
        ws.append(row_vals)

    # Apply uniform template styling across all rows via iter_rows for optimal performance
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(ALLOCATION_COLUMNS)):
        is_spare = (row[status_col_idx - 1].value == "WIRED SPARE")
        seg = row[seg_col_idx - 1].value
        for col_idx, cell in enumerate(row, start=1):
            cell.border = thin_border
            cell.alignment = center_align if col_idx in center_cols else left_align
            if is_spare:
                cell.font = spare_font
                cell.fill = spare_fill
            elif col_idx == seg_col_idx:
                if seg == "A":
                    cell.font = train_a_font
                elif seg == "B":
                    cell.font = train_b_font

    _auto_fit_columns(ws, min_width=12)
    ws.freeze_panes = "A2"


def _populate_tq_sheet(ws, tqs: Optional[Sequence[TechnicalQuery]]) -> None:
    """Populate and format the TQ_Log worksheet."""
    tq_header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    tq_header_fill = PatternFill(start_color="800000", end_color="800000", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    for col_idx, (col_name, _) in enumerate(TQ_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = tq_header_font
        cell.fill = tq_header_fill
        cell.alignment = center_align

    if tqs:
        crit_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        crit_font = Font(name="Calibri", size=10, bold=True, color="9C0006")
        warn_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        warn_font = Font(name="Calibri", size=10, bold=True, color="9C6500")

        for row_idx, tq in enumerate(tqs, start=2):
            sev_str = getattr(tq.severity, "value", str(tq.severity))
            for col_idx, (_, attr_name) in enumerate(TQ_COLUMNS, start=1):
                val = getattr(tq, attr_name)
                if hasattr(val, "value"):
                    val = val.value
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border

                if attr_name == "severity":
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    if sev_str == "Critical":
                        cell.fill = crit_fill
                        cell.font = crit_font
                    elif sev_str == "Warning":
                        cell.fill = warn_fill
                        cell.font = warn_font
                elif attr_name == "tq_id":
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = Font(name="Calibri", size=10, bold=True)
                else:
                    cell.alignment = left_align

    _auto_fit_columns(ws, min_width=14)
    ws.freeze_panes = "A2"


def _populate_cabinet_summary_sheet(
    ws,
    allocations: Sequence[AllocatedSignal],
    ciocs_per_cabinet: int = 4,
    bps_per_cioc: int = 8,
    charms_per_bp: int = 12,
) -> None:
    """Populate and format the Cabinet_Summary worksheet."""
    cab_header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    cab_header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    for col_idx, (col_name, _) in enumerate(CABINET_SUMMARY_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = cab_header_font
        cell.fill = cab_header_fill
        cell.alignment = center_align

    records, overall = compute_cabinet_summary(
        allocations,
        ciocs_per_cabinet=ciocs_per_cabinet,
        bps_per_cioc=bps_per_cioc,
        charms_per_bp=charms_per_bp,
    )

    current_row = 2
    for record in records:
        for col_idx, (_, attr_name) in enumerate(CABINET_SUMMARY_COLUMNS, start=1):
            val = getattr(record, attr_name)
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.border = thin_border
            if attr_name in ("cabinet_id", "ciocs_list", "utilization_str"):
                cell.alignment = center_align
                if attr_name == "cabinet_id":
                    cell.font = Font(name="Calibri", size=10, bold=True)
            else:
                cell.alignment = right_align
        current_row += 1

    # Total summary row
    tot_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    tot_font = Font(name="Calibri", size=11, bold=True, color="002060")
    tot_border = Border(
        left=Side(style="thin", color="1F497D"),
        right=Side(style="thin", color="1F497D"),
        top=Side(style="thin", color="1F497D"),
        bottom=Side(style="double", color="1F497D"),
    )

    tot_vals = {
        "cabinet_id": "TOTAL",
        "ciocs_list": f"{overall.total_ciocs} CIOCs Active",
        "total_capacity": overall.total_capacity,
        "active_loops": overall.total_active_loops,
        "wired_spares": overall.total_wired_spares,
        "total_allocated": overall.total_allocated,
        "free_spares": overall.total_free_spares,
        "utilization_str": overall.utilization_str,
    }

    for col_idx, (_, attr_name) in enumerate(CABINET_SUMMARY_COLUMNS, start=1):
        cell = ws.cell(row=current_row, column=col_idx, value=tot_vals[attr_name])
        cell.font = tot_font
        cell.fill = tot_fill
        cell.border = tot_border
        cell.alignment = center_align if attr_name in ("cabinet_id", "ciocs_list", "utilization_str") else right_align

    _auto_fit_columns(ws, min_width=14)
    ws.freeze_panes = "A2"


def _populate_rule_compliance_sheet(
    ws,
    allocations: Sequence[AllocatedSignal],
    tqs: Optional[Sequence[TechnicalQuery]] = None,
    charms_per_bp: int = 12,
    bps_per_cioc: int = 8,
    segregation_policy: Union[str, SegregationPolicy] = SegregationPolicy.CIOC,
    ciocs_per_cabinet: int = 4,
) -> None:
    """Populate and format the Rule_Compliance worksheet."""
    rule_header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    rule_header_fill = PatternFill(start_color="1E4620", end_color="1E4620", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    for col_idx, (col_name, _) in enumerate(RULE_COMPLIANCE_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = rule_header_font
        cell.fill = rule_header_fill
        cell.alignment = center_align

    items, summary = generate_rule_compliance_audit(
        allocations,
        tqs=tqs,
        charms_per_bp=charms_per_bp,
        bps_per_cioc=bps_per_cioc,
        segregation_policy=segregation_policy,
        ciocs_per_cabinet=ciocs_per_cabinet,
    )

    pass_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    pass_font = Font(name="Calibri", size=10, bold=True, color="006100")
    fail_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    fail_font = Font(name="Calibri", size=10, bold=True, color="9C0006")

    for row_idx, item in enumerate(items, start=2):
        for col_idx, (_, attr_name) in enumerate(RULE_COMPLIANCE_COLUMNS, start=1):
            val = getattr(item, attr_name)
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border

            if attr_name == "status":
                cell.alignment = center_align
                if val == "PASS":
                    cell.fill = pass_fill
                    cell.font = pass_font
                else:
                    cell.fill = fail_fill
                    cell.font = fail_font
            elif attr_name in ("rule_id", "category", "tested_count", "violations"):
                cell.alignment = center_align
                if attr_name == "rule_id":
                    cell.font = Font(name="Calibri", size=10, bold=True)
            else:
                cell.alignment = left_align

    _auto_fit_columns(ws, min_width=14)
    ws.freeze_panes = "A2"


def export_allocation_to_excel(
    allocations: Sequence[AllocatedSignal],
    output_path_or_buffer: Optional[Union[str, Path, BinaryIO]] = None,
    tqs: Optional[Sequence[TechnicalQuery]] = None,
    template_path_or_buffer: Optional[Union[str, Path, BinaryIO, bytes]] = None,
    charms_per_bp: int = 12,
    bps_per_cioc: int = 8,
    ciocs_per_cabinet: int = 4,
    segregation_policy: Union[str, SegregationPolicy] = SegregationPolicy.CIOC,
    revision_result: Optional[Any] = None,
    rev_a_allocations: Optional[Sequence[AllocatedSignal]] = None,
) -> bytes:
    """Export allocated signals to a complete deliverable Excel workbook (.xlsx).

    Tabs generated:
      1. Customer Template Sheet (injected) or Template_Overlay
      2. Allocation (DeltaV hardware allocation matrix)
      3. TQ_Log (Formal technical queries log)
      4. Cabinet_Summary (Channel counts, wired spares, free spares, utilization %)
      5. Rule_Compliance (Independent audit checklist with pass/fail counts)
      6. Revision_Impact (Optional customer revision comparison matrix)

    Args:
        allocations: Sequence of AllocatedSignal objects.
        output_path_or_buffer: Optional file path or buffer to write to.
        tqs: Optional sequence of TechnicalQuery records to write to TQ_Log.
        template_path_or_buffer: Optional blank customer Excel template to overlay data onto.
        charms_per_bp: CHARMs per baseplate (12).
        bps_per_cioc: Baseplates per CIOC (8).
        ciocs_per_cabinet: CIOCs per cabinet (4).
        segregation_policy: "CIOC" or "CABINET" segregation verification policy.
        revision_result: Optional RevisionAllocationResult from revision diff engine.
        rev_a_allocations: Optional baseline Rev A allocated signals.

    Returns:
        Raw bytes of the generated Excel workbook.
    """
    if template_path_or_buffer is not None:
        wb = overlay_allocation_on_template(template_path_or_buffer, allocations)

        # Tab 2: Allocation
        if "Allocation" not in wb.sheetnames:
            ws_alloc = wb.create_sheet(title="Allocation")
            _populate_allocation_sheet(ws_alloc, allocations)

        # Tab 3: TQ_Log
        if "TQ_Log" not in wb.sheetnames:
            ws_tq = wb.create_sheet(title="TQ_Log")
        else:
            ws_tq = wb["TQ_Log"]
        _populate_tq_sheet(ws_tq, tqs)

        # Tab 4: Cabinet_Summary
        if "Cabinet_Summary" not in wb.sheetnames:
            ws_cab = wb.create_sheet(title="Cabinet_Summary")
        else:
            ws_cab = wb["Cabinet_Summary"]
        _populate_cabinet_summary_sheet(
            ws_cab, allocations, ciocs_per_cabinet=ciocs_per_cabinet,
            bps_per_cioc=bps_per_cioc, charms_per_bp=charms_per_bp
        )

        # Tab 5: Rule_Compliance
        if "Rule_Compliance" not in wb.sheetnames:
            ws_rule = wb.create_sheet(title="Rule_Compliance")
        else:
            ws_rule = wb["Rule_Compliance"]
        _populate_rule_compliance_sheet(
            ws_rule, allocations, tqs=tqs,
            charms_per_bp=charms_per_bp, bps_per_cioc=bps_per_cioc,
            segregation_policy=segregation_policy, ciocs_per_cabinet=ciocs_per_cabinet
        )

    else:
        wb = openpyxl.Workbook()

        # Tab 1: Allocation
        ws_alloc = wb.active
        ws_alloc.title = "Allocation"
        _populate_allocation_sheet(ws_alloc, allocations)

        # Tab 2: TQ_Log
        ws_tq = wb.create_sheet(title="TQ_Log")
        _populate_tq_sheet(ws_tq, tqs)

        # Tab 3: Cabinet_Summary
        ws_cab = wb.create_sheet(title="Cabinet_Summary")
        _populate_cabinet_summary_sheet(
            ws_cab, allocations, ciocs_per_cabinet=ciocs_per_cabinet,
            bps_per_cioc=bps_per_cioc, charms_per_bp=charms_per_bp
        )

        # Tab 4: Rule_Compliance
        ws_rule = wb.create_sheet(title="Rule_Compliance")
        _populate_rule_compliance_sheet(
            ws_rule, allocations, tqs=tqs,
            charms_per_bp=charms_per_bp, bps_per_cioc=bps_per_cioc,
            segregation_policy=segregation_policy, ciocs_per_cabinet=ciocs_per_cabinet
        )

        # Tab 5: Template_Overlay (sample preview when no customer template is supplied)
        ws_overlay = wb.create_sheet(title="Template_Overlay")
        sample_allocs = allocations[:250] if len(allocations) > 250 else allocations
        _populate_allocation_sheet(ws_overlay, sample_allocs)

    # Tab: Revision_Impact (appended when revision_result is supplied)
    if revision_result is not None:
        from src.revision.excel_tab import populate_revision_impact_sheet

        if "Revision_Impact" not in wb.sheetnames:
            ws_rev = wb.create_sheet(title="Revision_Impact")
        else:
            ws_rev = wb["Revision_Impact"]
        populate_revision_impact_sheet(ws_rev, revision_result, rev_a_allocations or [])

    # Save workbook to buffer
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
