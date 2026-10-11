import pytest

from src.ingestion.mapper import auto_map_columns


def test_auto_map_standard_columns():
    headers = ["Tag", "IO Type", "Cable ID", "Pair No", "Description", "IO Group", "Segregation"]
    mapping = auto_map_columns(headers)

    assert mapping["tag"] == "Tag"
    assert mapping["io_type"] == "IO Type"
    assert mapping["cable_id"] == "Cable ID"
    assert mapping["pair_no"] == "Pair No"
    assert mapping["description"] == "Description"
    assert mapping["io_group"] == "IO Group"
    assert mapping["segregation"] == "Segregation"


def test_auto_map_customer_variant_headers():
    headers = [
        "Instrument Tag",
        "Signal Type",
        "Trunk Cable",
        "Wire Pair",
        "Tag Description",
        "Plant Area",
        "Safety Train",
    ]
    mapping = auto_map_columns(headers)

    assert mapping["tag"] == "Instrument Tag"
    assert mapping["io_type"] == "Signal Type"
    assert mapping["cable_id"] == "Trunk Cable"
    assert mapping["pair_no"] == "Wire Pair"
    assert mapping["description"] == "Tag Description"
    assert mapping["io_group"] == "Plant Area"
    assert mapping["segregation"] == "Safety Train"


def test_auto_map_regex_and_case_variants():
    headers = [
        "TAG_NUMBER",
        "I/O TYPE",
        "CABLE_NO",
        "PAIR #",
        "SERVICE",
        "UNIT",
        "TRAIN",
    ]
    mapping = auto_map_columns(headers)

    assert mapping["tag"] == "TAG_NUMBER"
    assert mapping["io_type"] == "I/O TYPE"
    assert mapping["cable_id"] == "CABLE_NO"
    assert mapping["pair_no"] == "PAIR #"
    assert mapping["description"] == "SERVICE"
    assert mapping["io_group"] == "UNIT"
    assert mapping["segregation"] == "TRAIN"


def test_auto_map_missing_required_columns_reports_unmapped():
    headers = ["Description", "Cable ID", "Pair No"]
    mapping = auto_map_columns(headers)

    assert "tag" not in mapping
    assert "io_type" not in mapping
    assert mapping["description"] == "Description"
