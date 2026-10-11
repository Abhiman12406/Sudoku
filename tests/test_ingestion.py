import io
import pandas as pd
import pytest
from pydantic import ValidationError

from src.domain.models import IOType, Signal
from src.ingestion.parser import parse_signal_file


def create_sample_excel_bytes() -> bytes:
    data = {
        "Tag": ["10-FT-101", "10-FV-101", "10-PSH-102", "10-XV-102"],
        "IO Type": ["AI", "AO", "DI", "DO"],
        "Cable ID": ["CBL-01", "CBL-01", "CBL-01", "CBL-01"],
        "Pair No": [1, 2, 3, 4],
        "Description": ["Flow Transmitter", "Flow Control Valve", "Pressure Switch High", "Shutdown Valve"],
    }
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Signals")
    return buf.getvalue()


def test_parse_valid_excel_signals():
    excel_bytes = create_sample_excel_bytes()
    signals = parse_signal_file(io.BytesIO(excel_bytes))

    assert len(signals) == 4
    assert signals[0].tag == "10-FT-101"
    assert signals[0].io_type == IOType.AI
    assert signals[0].cable_id == "CBL-01"
    assert signals[0].pair_no == 1
    assert signals[0].description == "Flow Transmitter"

    assert signals[1].tag == "10-FV-101"
    assert signals[1].io_type == IOType.AO

    assert signals[2].tag == "10-PSH-102"
    assert signals[2].io_type == IOType.DI

    assert signals[3].tag == "10-XV-102"
    assert signals[3].io_type == IOType.DO


def test_parse_invalid_io_type_raises_error():
    data = {
        "Tag": ["10-FT-999"],
        "IO Type": ["INVALID_TYPE"],
        "Cable ID": ["CBL-01"],
        "Pair No": [1],
    }
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    with pytest.raises((ValueError, ValidationError)):
        parse_signal_file(io.BytesIO(buf.getvalue()))
