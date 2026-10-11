import io
import openpyxl
import pandas as pd
import pytest

from src.domain.models import IOType, AllocatedSignal
from src.export.excel_export import export_allocation_to_excel


def test_export_allocation_to_excel_bytes():
    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            baseplate=1,
            slot=1,
            cable_id="CBL-01",
            pair_no=1,
            description="Flow Transmitter",
            charm_part_no="KL3001X1-BA1",
            terminal_block_type="Standard",
        ),
        AllocatedSignal(
            tag="10-XV-102",
            io_type=IOType.DO,
            baseplate=1,
            slot=2,
            cable_id="CBL-01",
            pair_no=2,
            description="Shutdown Valve",
            charm_part_no="KL3004X1-BA1",
            terminal_block_type="Fused Injected-Power",
        ),
    ]

    excel_bytes = export_allocation_to_excel(allocations)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    # Read back with pandas/openpyxl to verify content
    df = pd.read_excel(io.BytesIO(excel_bytes))
    assert len(df) == 2

    # Check required columns
    expected_cols = [
        "Tag", "IO Type", "Baseplate", "Slot", "Cable ID", "Pair No",
        "CHARM Part No", "Terminal Block Type", "Description"
    ]
    for col in expected_cols:
        assert col in df.columns

    # Verify rows
    assert df.loc[0, "Tag"] == "10-FT-101"
    assert df.loc[0, "Baseplate"] == 1
    assert df.loc[0, "Slot"] == 1
    assert df.loc[0, "CHARM Part No"] == "KL3001X1-BA1"

    assert df.loc[1, "Tag"] == "10-XV-102"
    assert df.loc[1, "Baseplate"] == 1
    assert df.loc[1, "Slot"] == 2
    assert df.loc[1, "Terminal Block Type"] == "Fused Injected-Power"


def test_export_empty_allocation():
    excel_bytes = export_allocation_to_excel([])
    df = pd.read_excel(io.BytesIO(excel_bytes))
    assert len(df) == 0
    assert "Tag" in df.columns
    assert "Slot" in df.columns


def test_export_includes_tq_log_sheet():
    from src.domain.models import Severity, TechnicalQuery

    tqs = [
        TechnicalQuery(
            tq_id="TQ-INST-001",
            category="Duplicate Tag",
            impacted_tag="10-FT-101",
            description="Duplicate tag found in rows 2 and 5.",
            severity=Severity.CRITICAL,
            recommended_remedy="Rename duplicate tag.",
            row_number=5,
        ),
        TechnicalQuery(
            tq_id="TQ-INST-002",
            category="Capacity Overflow",
            impacted_tag="10-PT-102",
            description="Pair 25 exceeds maximum 24 pairs.",
            severity=Severity.CRITICAL,
            recommended_remedy="Reassign within 24 pairs.",
            row_number=7,
        ),
    ]

    excel_bytes = export_allocation_to_excel([], tqs=tqs)
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

    assert "Allocation" in wb.sheetnames
    assert "TQ_Log" in wb.sheetnames

    df_tq = pd.read_excel(io.BytesIO(excel_bytes), sheet_name="TQ_Log")
    assert len(df_tq) == 2
    assert "TQ ID" in df_tq.columns
    assert "Severity" in df_tq.columns
    assert "Category" in df_tq.columns
    assert "Impacted Tag" in df_tq.columns
    assert "Description" in df_tq.columns
    assert "Recommended Remedy" in df_tq.columns

    assert df_tq.loc[0, "TQ ID"] == "TQ-INST-001"
    assert df_tq.loc[0, "Severity"] == "Critical"
    assert df_tq.loc[0, "Category"] == "Duplicate Tag"
    assert df_tq.loc[1, "TQ ID"] == "TQ-INST-002"


def test_export_includes_cabinet_summary_sheet():
    allocations = [
        AllocatedSignal(
            tag=f"10-FT-{i:03d}",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=i,
            is_spare=False,
        )
        for i in range(1, 11)
    ] + [
        AllocatedSignal(
            tag="WIRED SPARE",
            io_type=IOType.SPARE,
            cioc=1,
            baseplate=1,
            slot=11,
            is_spare=True,
        ),
        AllocatedSignal(
            tag="WIRED SPARE",
            io_type=IOType.SPARE,
            cioc=1,
            baseplate=1,
            slot=12,
            is_spare=True,
        ),
    ]

    excel_bytes = export_allocation_to_excel(allocations)
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

    assert "Cabinet_Summary" in wb.sheetnames

    df_cab = pd.read_excel(io.BytesIO(excel_bytes), sheet_name="Cabinet_Summary")
    assert "Cabinet ID" in df_cab.columns
    assert "Total Capacity" in df_cab.columns
    assert "Active Loops" in df_cab.columns
    assert "Wired Spares" in df_cab.columns
    assert "Free Spares" in df_cab.columns
    assert "Utilization %" in df_cab.columns

    # Verify CAB-01 row
    cab1 = df_cab[df_cab["Cabinet ID"] == "CAB-01"].iloc[0]
    assert cab1["Active Loops"] == 10
    assert cab1["Wired Spares"] == 2
    assert cab1["Total Allocated"] == 12
    assert cab1["Free Spares"] == cab1["Total Capacity"] - 12
    assert float(cab1["Utilization %"].replace("%", "")) > 0


def test_export_includes_rule_compliance_sheet():
    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
            cable_id="CBL-01",
            pair_no=1,
            charm_part_no="KL3001X1-BA1",
            terminal_block_type="Standard",
        ),
        AllocatedSignal(
            tag="10-FT-102",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=2,
            cable_id="CBL-01",
            pair_no=2,
            charm_part_no="KL3001X1-BA1",
            terminal_block_type="Standard",
        ),
    ]

    excel_bytes = export_allocation_to_excel(allocations)
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

    assert "Rule_Compliance" in wb.sheetnames

    # Read Rule_Compliance sheet
    df_rules = pd.read_excel(io.BytesIO(excel_bytes), sheet_name="Rule_Compliance")
    assert "Rule ID" in df_rules.columns
    assert "Rule Name" in df_rules.columns
    assert "Violations" in df_rules.columns
    assert "Status" in df_rules.columns

    # Verify all invariants have passed
    assert len(df_rules) >= 6
    for _, row in df_rules.iterrows():
        assert row["Status"] in ("PASS", "PASSED", "Pass", "100% PASS")
        assert row["Violations"] == 0


def test_template_overlay_preserves_styles_and_formulas():
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from src.export.template_overlay import overlay_allocation_on_template

    # 1. Create a mock customer template workbook with distinct styles & formulas
    wb_template = openpyxl.Workbook()
    ws = wb_template.active
    ws.title = "Customer_Schedule"

    header_font = Font(name="Arial", size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
    data_font = Font(name="Calibri", size=10, italic=True, color="333333")
    data_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000"),
    )

    headers = ["Loop Tag", "Signal Type", "Cabinet", "CIOC", "Baseplate", "Slot", "Cable", "Pair", "Calculated Code"]
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center")

    # Row 2 style template with an Excel formula
    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(row=2, column=col_idx)
        c.font = data_font
        c.fill = data_fill
        c.border = thin_border

    # In cell I2 (column 9), put a customer formula
    ws.cell(row=2, column=9, value='=CONCATENATE(A2, "-", B2)')
    ws.column_dimensions["A"].width = 28

    buf_template = io.BytesIO()
    wb_template.save(buf_template)
    template_bytes = buf_template.getvalue()

    # 2. Allocations to overlay
    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
            cable_id="CBL-01",
            pair_no=1,
        ),
        AllocatedSignal(
            tag="10-XV-102",
            io_type=IOType.DO,
            cioc=1,
            baseplate=1,
            slot=2,
            cable_id="CBL-01",
            pair_no=2,
        ),
    ]

    # 3. Apply template overlay
    out_wb = overlay_allocation_on_template(template_bytes, allocations)
    out_ws = out_wb["Customer_Schedule"]

    # Verify headers preserved
    assert out_ws.cell(row=1, column=1).value == "Loop Tag"
    assert out_ws.cell(row=1, column=1).font.bold is True
    assert out_ws.column_dimensions["A"].width == 28

    # Verify injected data in exact columns starting at row 2
    assert out_ws.cell(row=2, column=1).value == "10-FT-101"
    assert out_ws.cell(row=2, column=2).value == "AI"
    assert out_ws.cell(row=2, column=3).value in ("CAB-01", 1)
    assert out_ws.cell(row=2, column=4).value in ("CIOC-01", 1)
    assert out_ws.cell(row=2, column=5).value == 1
    assert out_ws.cell(row=2, column=6).value == 1
    assert out_ws.cell(row=2, column=7).value == "CBL-01"
    assert out_ws.cell(row=2, column=8).value == 1

    assert out_ws.cell(row=3, column=1).value == "10-XV-102"
    assert out_ws.cell(row=3, column=2).value == "DO"
    assert out_ws.cell(row=3, column=5).value == 1
    assert out_ws.cell(row=3, column=6).value == 2

    # Verify formatting preserved for both rows
    assert out_ws.cell(row=2, column=1).font.italic is True
    assert out_ws.cell(row=3, column=1).font.italic is True
    assert out_ws.cell(row=3, column=1).fill.start_color.rgb == "00E2EFDA" or out_ws.cell(row=3, column=1).fill.fill_type == "solid"
    assert out_ws.cell(row=3, column=1).border.left.style == "thin"

    # Verify formula preserved and adjusted for row 3
    assert out_ws.cell(row=2, column=9).value == '=CONCATENATE(A2, "-", B2)'
    assert out_ws.cell(row=3, column=9).value == '=CONCATENATE(A3, "-", B3)'


def test_export_complete_5_tab_deliverable_package_with_template():
    # Create template
    wb_template = openpyxl.Workbook()
    ws = wb_template.active
    ws.title = "Client_Deliverable"
    ws.cell(row=1, column=1, value="Tag")
    ws.cell(row=1, column=2, value="IO Type")
    buf_template = io.BytesIO()
    wb_template.save(buf_template)
    template_bytes = buf_template.getvalue()

    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
            cable_id="CBL-01",
            pair_no=1,
            charm_part_no="KL3001X1-BA1",
            terminal_block_type="Standard",
        )
    ]

    excel_bytes = export_allocation_to_excel(
        allocations,
        template_path_or_buffer=template_bytes,
    )
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

    # All 5 tabs present: Customer Template + Allocation + TQ_Log + Cabinet_Summary + Rule_Compliance
    assert len(wb.sheetnames) == 5
    assert "Client_Deliverable" in wb.sheetnames
    assert "Allocation" in wb.sheetnames
    assert "TQ_Log" in wb.sheetnames
    assert "Cabinet_Summary" in wb.sheetnames
    assert "Rule_Compliance" in wb.sheetnames


def test_export_5_tab_package_without_template():
    allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cioc=1,
            baseplate=1,
            slot=1,
        )
    ]
    excel_bytes = export_allocation_to_excel(allocations)
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))

    # In default mode without uploaded template, deliverable package provides 5 tabs
    assert len(wb.sheetnames) == 5
    assert "Allocation" in wb.sheetnames
    assert "TQ_Log" in wb.sheetnames
    assert "Cabinet_Summary" in wb.sheetnames
    assert "Rule_Compliance" in wb.sheetnames
    assert "Template_Overlay" in wb.sheetnames





