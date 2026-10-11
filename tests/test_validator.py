import pandas as pd
import pytest

from src.domain.models import IOType, Severity, Signal, TechnicalQuery
from src.ingestion.validator import validate_dataframe


def test_validate_clean_dataframe():
    df = pd.DataFrame({
        "Tag": ["10-FT-101", "10-FV-101"],
        "IO Type": ["AI", "AO"],
        "Cable ID": ["CBL-01", "CBL-01"],
        "Pair No": [1, 2],
        "Description": ["Flow Transmitter", "Flow Valve"],
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(tqs) == 0
    assert len(valid_signals) == 2
    assert valid_signals[0].tag == "10-FT-101"
    assert valid_signals[1].tag == "10-FV-101"


def test_validate_missing_tag():
    df = pd.DataFrame({
        "Tag": [None, "10-FV-101"],
        "IO Type": ["AI", "AO"],
        "Cable ID": ["CBL-01", "CBL-01"],
        "Pair No": [1, 2],
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 1
    assert valid_signals[0].tag == "10-FV-101"
    assert len(tqs) == 1
    assert tqs[0].tq_id == "TQ-INST-001"
    assert tqs[0].category == "Missing Field"
    assert tqs[0].severity == Severity.CRITICAL
    assert "Missing" in tqs[0].description


def test_validate_duplicate_tags():
    df = pd.DataFrame({
        "Tag": ["10-FT-101", "10-FT-101", "10-PT-102"],
        "IO Type": ["AI", "AI", "AI"],
        "Cable ID": ["CBL-01", "CBL-01", "CBL-01"],
        "Pair No": [1, 2, 3],
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 1
    assert valid_signals[0].tag == "10-PT-102"
    assert len(tqs) == 1
    assert tqs[0].tq_id == "TQ-INST-001"
    assert tqs[0].category == "Duplicate Tag"
    assert tqs[0].impacted_tag == "10-FT-101"
    assert tqs[0].severity == Severity.CRITICAL
    assert "duplicate" in tqs[0].description.lower()


def test_validate_unknown_io_type():
    df = pd.DataFrame({
        "Tag": ["10-FT-101", "10-BAD-999"],
        "IO Type": ["AI", "UNKNOWN_TYPE"],
        "Cable ID": ["CBL-01", "CBL-01"],
        "Pair No": [1, 2],
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 1
    assert valid_signals[0].tag == "10-FT-101"
    assert len(tqs) == 1
    assert tqs[0].tq_id == "TQ-INST-001"
    assert tqs[0].category == "Unknown IO Type"
    assert tqs[0].impacted_tag == "10-BAD-999"
    assert tqs[0].severity == Severity.CRITICAL


def test_validate_pair_overflow_exceeding_max_cable_capacity():
    df = pd.DataFrame({
        "Tag": ["10-FT-101", "10-FT-102"],
        "IO Type": ["AI", "AI"],
        "Cable ID": ["CBL-01", "CBL-01"],
        "Pair No": [1, 25],  # 25 exceeds max 24 pairs
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 1
    assert valid_signals[0].tag == "10-FT-101"
    assert len(tqs) == 1
    assert tqs[0].tq_id == "TQ-INST-001"
    assert tqs[0].category == "Capacity Overflow"
    assert tqs[0].impacted_tag == "10-FT-102"
    assert tqs[0].severity == Severity.CRITICAL


def test_validate_segregation_conflict_in_same_cable():
    df = pd.DataFrame({
        "Tag": ["10-FT-101", "10-FT-102", "20-FT-201"],
        "IO Type": ["AI", "AI", "AI"],
        "Cable ID": ["CBL-01", "CBL-01", "CBL-02"],
        "Pair No": [1, 2, 1],
        "Segregation": ["A", "B", "A"],
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 1
    assert valid_signals[0].tag == "20-FT-201"
    assert len(tqs) >= 1
    conflict_tq = next((t for t in tqs if t.category == "Segregation Conflict"), None)
    assert conflict_tq is not None
    assert conflict_tq.severity == Severity.CRITICAL


def test_validate_missing_required_column():
    df = pd.DataFrame({
        "Description": ["Pressure Transmitter"],
        "Cable ID": ["CBL-01"],
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 0
    assert len(tqs) >= 1
    assert tqs[0].category == "Missing Field"


def test_validate_declared_cable_size_overflow():
    df = pd.DataFrame({
        "Tag": ["10-FT-101", "10-FT-102"],
        "IO Type": ["AI", "AI"],
        "Cable ID": ["CBL-01", "CBL-01"],
        "Pair No": [1, 7],
        "Cable Size": [6, 6],  # 6-pair cable, pair 7 overflows
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 1
    assert valid_signals[0].tag == "10-FT-101"
    assert len(tqs) == 1
    assert tqs[0].category == "Capacity Overflow"
    assert tqs[0].impacted_tag == "10-FT-102"


def test_validate_duplicate_pair_in_same_cable():
    df = pd.DataFrame({
        "Tag": ["10-FT-101", "10-FT-102", "10-FT-103"],
        "IO Type": ["AI", "AI", "AI"],
        "Cable ID": ["CBL-01", "CBL-01", "CBL-02"],
        "Pair No": [1, 1, 1],  # 101 and 102 share pair 1 on CBL-01
    })
    valid_signals, tqs = validate_dataframe(df)

    assert len(valid_signals) == 1
    assert valid_signals[0].tag == "10-FT-103"
    assert len(tqs) == 1
    assert tqs[0].category == "Duplicate Pair Number"

