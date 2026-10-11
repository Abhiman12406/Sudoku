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
