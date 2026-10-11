import io
import pandas as pd
import pytest

from src.pipeline import run_walking_pipeline


def test_run_walking_pipeline_end_to_end():
    # Create sample Excel input buffer
    df_in = pd.DataFrame({
        "Tag": ["10-PT-101", "10-TT-102", "10-ZS-103", "10-SOV-104"],
        "IO Type": ["AI", "AI", "DI", "DO"],
        "Cable ID": ["TRUNK-A", "TRUNK-A", "TRUNK-A", "TRUNK-A"],
        "Pair No": [1, 2, 3, 4],
        "Description": ["Pressure Transmitter", "Temperature Transmitter", "Limit Switch", "Solenoid"],
    })
    in_buf = io.BytesIO()
    with pd.ExcelWriter(in_buf, engine="openpyxl") as writer:
        df_in.to_excel(writer, index=False)
    in_bytes = in_buf.getvalue()

    allocations, out_bytes = run_walking_pipeline(io.BytesIO(in_bytes), charms_per_baseplate=12)

    assert len(allocations) == 4
    assert len(out_bytes) > 0

    # Verify allocations structure
    tags = [a.tag for a in allocations]
    assert "10-PT-101" in tags
    assert "10-SOV-104" in tags
    for a in allocations:
        assert a.baseplate == 1
        assert 1 <= a.slot <= 12

    # Verify generated output Excel
    df_out = pd.read_excel(io.BytesIO(out_bytes))
    assert len(df_out) == 4
    assert set(df_out["Tag"]) == {"10-PT-101", "10-TT-102", "10-ZS-103", "10-SOV-104"}
    assert "Baseplate" in df_out.columns
    assert "Slot" in df_out.columns
    assert "CHARM Part No" in df_out.columns
