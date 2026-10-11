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
    assert "CHARM Part No" in df_out.columns


def test_run_hierarchical_pipeline_end_to_end():
    from src.pipeline import run_hierarchical_pipeline

    df_in = pd.DataFrame({
        "Tag": [f"10-FT-{i:02d}" for i in range(1, 11)],
        "IO Type": ["AI"] * 10,
        "Cable ID": ["TRUNK-12"] * 10,
        "Pair No": list(range(1, 11)),
        "Description": [f"Flow Transmitter {i}" for i in range(1, 11)],
    })
    in_buf = io.BytesIO()
    with pd.ExcelWriter(in_buf, engine="openpyxl") as writer:
        df_in.to_excel(writer, index=False)
    in_bytes = in_buf.getvalue()

    allocations, out_bytes = run_hierarchical_pipeline(io.BytesIO(in_bytes))

    # 12-pair cable: 10 active + 2 wired spares = 12 total allocations
    assert len(allocations) == 12
    spares = [a for a in allocations if a.is_spare]
    assert len(spares) == 2
    assert {s.pair_no for s in spares} == {11, 12}

    # Verify generated Excel deliverable
    df_out = pd.read_excel(io.BytesIO(out_bytes))
    assert len(df_out) == 12
    assert "WIRED SPARE" in list(df_out["Tag"])
    assert "CIOC" in df_out.columns


def test_run_walking_pipeline_corrupt_data_fault_tolerance():
    # Intentionally corrupt data: duplicate tags, pair overflow, invalid IO type
    df_corrupt = pd.DataFrame({
        "Tag": ["10-PT-101", "10-PT-101", "10-BAD-001", "10-OVF-002", "20-FT-201"],
        "IO Type": ["AI", "AI", "CORRUPT_TYPE", "AI", "AI"],
        "Cable ID": ["TRUNK-A", "TRUNK-A", "TRUNK-A", "TRUNK-A", "TRUNK-B"],
        "Pair No": [1, 1, 3, 30, 1],  # 30 exceeds 24 pairs
        "Description": ["Dup A", "Dup B", "Bad Type", "Overflow", "Valid Loop"],
    })
    in_buf = io.BytesIO()
    with pd.ExcelWriter(in_buf, engine="openpyxl") as writer:
        df_corrupt.to_excel(writer, index=False)
    in_bytes = in_buf.getvalue()

    result = run_walking_pipeline(io.BytesIO(in_bytes), charms_per_baseplate=12)

    # Backwards-compatible unpacking
    allocations, out_bytes = result

    # Only 20-FT-201 is valid and allocated
    assert len(allocations) == 1
    assert allocations[0].tag == "20-FT-201"

    # TQs were generated
    assert len(result.tqs) >= 3
    tq_ids = [t.tq_id for t in result.tqs]
    assert "TQ-INST-001" in tq_ids

    # Exported Excel contains both Allocation and TQ_Log
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(out_bytes))
    assert "Allocation" in wb.sheetnames
    assert "TQ_Log" in wb.sheetnames

    df_tqs_sheet = pd.read_excel(io.BytesIO(out_bytes), sheet_name="TQ_Log")
    assert len(df_tqs_sheet) >= 3
    assert "TQ ID" in df_tqs_sheet.columns
    assert "Severity" in df_tqs_sheet.columns
    assert "Recommended Remedy" in df_tqs_sheet.columns


def test_run_walking_pipeline_with_custom_catalog():
    df_in = pd.DataFrame({
        "Tag": ["10-PT-101", "10-TC-102"],
        "IO Type": ["AI", "TC"],
        "Cable ID": ["TRUNK-A", "TRUNK-A"],
        "Pair No": [1, 2],
        "Description": ["Pressure", "Thermocouple"],
    })
    in_buf = io.BytesIO()
    with pd.ExcelWriter(in_buf, engine="openpyxl") as writer:
        df_in.to_excel(writer, index=False)
    in_bytes = in_buf.getvalue()

    custom_cat = {
        "AI": {
            "charm_description": "Special Custom AI",
            "charm_part_no": "KL-SPECIAL-AI",
            "terminal_block_type": "Standard",
            "terminal_block_part_no": "KL-SPECIAL-TB",
        },
        "TC": {
            "charm_description": "Special Custom TC",
            "charm_part_no": "KL-SPECIAL-TC",
            "terminal_block_type": "CJC",
            "terminal_block_part_no": "KL-SPECIAL-CJC",
        },
    }

    allocations, out_bytes = run_walking_pipeline(
        io.BytesIO(in_bytes),
        charms_per_baseplate=12,
        catalog=custom_cat,
    )

    assert len(allocations) == 2
    assert allocations[0].charm_model == "Special Custom AI"
    assert allocations[0].charm_part_no == "KL-SPECIAL-AI"
    assert allocations[1].charm_model == "Special Custom TC"
    assert allocations[1].charm_part_no == "KL-SPECIAL-TC"

    df_out = pd.read_excel(io.BytesIO(out_bytes))
    assert df_out.loc[0, "CHARM Model"] == "Special Custom AI"
    assert df_out.loc[0, "CHARM Part No"] == "KL-SPECIAL-AI"


def test_run_hierarchical_pipeline_with_customer_template():
    import openpyxl
    from src.pipeline import run_hierarchical_pipeline

    # Create customer template
    wb_temp = openpyxl.Workbook()
    ws_temp = wb_temp.active
    ws_temp.title = "Client_Marshalling_Schedule"
    headers = ["Tag", "Signal Type", "Cabinet", "CIOC", "Baseplate", "Slot", "Cable", "Pair"]
    for c, h in enumerate(headers, 1):
        ws_temp.cell(row=1, column=c, value=h)
    temp_buf = io.BytesIO()
    wb_temp.save(temp_buf)
    temp_bytes = temp_buf.getvalue()

    df_in = pd.DataFrame({
        "Tag": ["10-FT-01", "10-FT-02"],
        "IO Type": ["AI", "AI"],
        "Cable ID": ["CBL-12", "CBL-12"],
        "Pair No": [1, 2],
        "Description": ["Flow 1", "Flow 2"],
    })
    in_buf = io.BytesIO()
    with pd.ExcelWriter(in_buf, engine="openpyxl") as writer:
        df_in.to_excel(writer, index=False)
    in_bytes = in_buf.getvalue()

    result = run_hierarchical_pipeline(
        in_bytes,
        template_file_or_bytes=temp_bytes,
    )
    allocations, out_bytes = result
    wb_out = openpyxl.load_workbook(io.BytesIO(out_bytes))

    assert "Client_Marshalling_Schedule" in wb_out.sheetnames
    assert "Allocation" in wb_out.sheetnames
    assert "Cabinet_Summary" in wb_out.sheetnames
    assert "Rule_Compliance" in wb_out.sheetnames
    assert "TQ_Log" in wb_out.sheetnames
    assert len(wb_out.sheetnames) == 5



