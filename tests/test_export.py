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

