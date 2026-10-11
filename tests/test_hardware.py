import io
import json
import pandas as pd
import pytest
from pathlib import Path

from src.domain.hardware import (
    DEFAULT_CATALOG,
    load_hardware_catalog,
    resolve_hardware_assignment,
    resolve_hardware_for_io,
)
from src.domain.models import AllocatedSignal, HardwareAssignment, IOType, Signal
from src.export.excel_export import export_allocation_to_excel
from src.ingestion.parser import parse_signal_file


def test_load_hardware_catalog_default():
    cat = load_hardware_catalog()
    assert isinstance(cat, dict)
    for expected_key in ["AI", "AO", "DI", "DO", "DO_RELAY", "TC", "RTD"]:
        assert expected_key in cat
        entry = cat[expected_key]
        assert "charm_description" in entry or "charm_model" in entry
        assert "charm_part_no" in entry
        assert "terminal_block_type" in entry
        assert "terminal_block_part_no" in entry


def test_load_hardware_catalog_custom_file(tmp_path):
    custom_data = {
        "hardware_catalog": {
            "AI": {
                "charm_description": "Custom AI Model",
                "charm_part_no": "CUSTOM-AI-01",
                "terminal_block_type": "Standard",
                "terminal_block_part_no": "CUSTOM-TB-01",
            }
        }
    }
    custom_file = tmp_path / "custom_catalog.json"
    custom_file.write_text(json.dumps(custom_data), encoding="utf-8")

    cat = load_hardware_catalog(custom_file)
    assert "AI" in cat
    assert cat["AI"]["charm_part_no"] == "CUSTOM-AI-01"
    assert cat["AI"]["charm_description"] == "Custom AI Model"


def test_resolve_hardware_standard_types():
    # AI
    hw_ai = resolve_hardware_assignment(IOType.AI)
    assert hw_ai.charm_model == "Analog Input 4-20 mA HART"
    assert hw_ai.charm_part_no == "KL3001X1-BA1"
    assert hw_ai.terminal_block_type == "Standard"
    assert hw_ai.terminal_block_part_no == "KL4001X1-BA1"

    # AO
    hw_ao = resolve_hardware_assignment(IOType.AO)
    assert hw_ao.charm_model == "Analog Output 4-20 mA HART"
    assert hw_ao.charm_part_no == "KL3002X1-BA1"
    assert hw_ao.terminal_block_type == "Standard"
    assert hw_ao.terminal_block_part_no == "KL4001X1-BA1"

    # DI
    hw_di = resolve_hardware_assignment(IOType.DI)
    assert hw_di.charm_model == "Discrete Input 24 VDC Isolated"
    assert hw_di.charm_part_no == "KL3003X1-BA1"
    assert hw_di.terminal_block_type == "Standard"
    assert hw_di.terminal_block_part_no == "KL4001X1-BA1"

    # RTD
    hw_rtd = resolve_hardware_assignment(IOType.RTD)
    assert hw_rtd.charm_model == "RTD / Resistance Input"
    assert hw_rtd.charm_part_no == "KL3007X1-BA1"
    assert hw_rtd.terminal_block_type == "Standard"
    assert hw_rtd.terminal_block_part_no == "KL4001X1-BA1"


def test_resolve_hardware_thermocouple_rule():
    # TC -> CJC terminal block
    hw_tc = resolve_hardware_assignment(IOType.TC)
    assert hw_tc.charm_model == "Thermocouple / mV Input"
    assert hw_tc.charm_part_no == "KL3006X1-BA1"
    assert hw_tc.terminal_block_type == "CJC"
    assert hw_tc.terminal_block_part_no == "KL4004X1-BA1"


def test_resolve_hardware_solenoid_valve_rule():
    # DO standard / solenoid -> Fused Injected-Power terminal block
    hw_sov = resolve_hardware_assignment(
        IOType.DO,
        description="Emergency Blowdown Solenoid Valve",
        tag="10-SOV-101",
    )
    assert hw_sov.charm_model == "Discrete Output 24 VDC High-Side"
    assert hw_sov.charm_part_no == "KL3004X1-BA1"
    assert hw_sov.terminal_block_type == "Fused Injected-Power"
    assert hw_sov.terminal_block_part_no == "KL4002X1-BA1"


def test_resolve_hardware_relay_do_rule():
    # Explicit DO_RELAY enum
    hw_relay_enum = resolve_hardware_assignment(IOType.DO_RELAY)
    assert hw_relay_enum.charm_model == "Relay Output Form C Isolated"
    assert hw_relay_enum.charm_part_no == "KL3005X1-BA1"
    assert hw_relay_enum.terminal_block_type == "Relay Form C"
    assert hw_relay_enum.terminal_block_part_no == "KL4003X1-BA1"

    # Inferred from description / tag
    hw_inferred = resolve_hardware_assignment(
        IOType.DO,
        description="Dry Contact Interlock Relay Output",
        tag="10-RLY-201",
    )
    assert hw_inferred.charm_model == "Relay Output Form C Isolated"
    assert hw_inferred.charm_part_no == "KL3005X1-BA1"
    assert hw_inferred.terminal_block_type == "Relay Form C"
    assert hw_inferred.terminal_block_part_no == "KL4003X1-BA1"


def test_resolve_hardware_spare_channel():
    hw_spare = resolve_hardware_assignment(IOType.SPARE)
    assert hw_spare.charm_model == "Wired Spare"
    assert hw_spare.charm_part_no is None
    assert hw_spare.terminal_block_type == "Standard"
    assert hw_spare.terminal_block_part_no == "KL4001X1-BA1"


def test_custom_catalog_override():
    custom_catalog = {
        "AI": {
            "charm_description": "Custom High-Accuracy AI",
            "charm_part_no": "KL3001X1-CUSTOM",
            "terminal_block_type": "Fused Injected-Power",
            "terminal_block_part_no": "KL4002X1-CUSTOM",
        }
    }
    hw = resolve_hardware_assignment(IOType.AI, catalog=custom_catalog)
    assert hw.charm_model == "Custom High-Accuracy AI"
    assert hw.charm_part_no == "KL3001X1-CUSTOM"
    assert hw.terminal_block_type == "Fused Injected-Power"
    assert hw.terminal_block_part_no == "KL4002X1-CUSTOM"


def test_backward_compatible_resolve_hardware_for_io():
    part, tb = resolve_hardware_for_io(IOType.AI)
    assert part == "KL3001X1-BA1"
    assert tb == "Standard"

    part_tc, tb_tc = resolve_hardware_for_io(IOType.TC)
    assert part_tc == "KL3006X1-BA1"
    assert tb_tc == "CJC"

    part_do, tb_do = resolve_hardware_for_io(IOType.DO)
    assert part_do == "KL3004X1-BA1"
    assert tb_do == "Fused Injected-Power"

    part_relay, tb_relay = resolve_hardware_for_io(IOType.DO_RELAY)
    assert part_relay == "KL3005X1-BA1"
    assert tb_relay == "Relay Form C"


def test_ingestion_supports_do_relay():
    df = pd.DataFrame({
        "Tag": ["10-RLY-101", "10-RLY-102", "10-RLY-103"],
        "IO Type": ["DO_RELAY", "RELAY", "DO-RELAY"],
        "Cable ID": ["CBL-01", "CBL-01", "CBL-01"],
        "Pair No": [1, 2, 3],
        "Description": ["Interlock Relay 1", "Interlock Relay 2", "Interlock Relay 3"],
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    signals = parse_signal_file(io.BytesIO(buf.getvalue()))
    assert len(signals) == 3
    for s in signals:
        assert s.io_type == IOType.DO_RELAY


def test_export_excel_includes_charm_model_and_tb_type():
    allocations = [
        AllocatedSignal(
            tag="10-TT-101",
            io_type=IOType.TC,
            cioc=1,
            baseplate=1,
            slot=1,
            charm_model="Thermocouple / mV Input",
            charm_part_no="KL3006X1-BA1",
            terminal_block_type="CJC",
            terminal_block_part_no="KL4004X1-BA1",
            description="Furnace Thermocouple",
        ),
        AllocatedSignal(
            tag="10-SOV-102",
            io_type=IOType.DO,
            cioc=1,
            baseplate=1,
            slot=2,
            charm_model="Discrete Output 24 VDC High-Side",
            charm_part_no="KL3004X1-BA1",
            terminal_block_type="Fused Injected-Power",
            terminal_block_part_no="KL4002X1-BA1",
            description="Blowdown Solenoid",
        ),
    ]

    excel_bytes = export_allocation_to_excel(allocations)
    df = pd.read_excel(io.BytesIO(excel_bytes))

    assert "CHARM Model" in df.columns
    assert "Terminal Block Type" in df.columns
    assert "CHARM Part No" in df.columns
    assert "Terminal Block Part No" in df.columns

    assert df.loc[0, "CHARM Model"] == "Thermocouple / mV Input"
    assert df.loc[0, "Terminal Block Type"] == "CJC"
    assert df.loc[1, "CHARM Model"] == "Discrete Output 24 VDC High-Side"
    assert df.loc[1, "Terminal Block Type"] == "Fused Injected-Power"
