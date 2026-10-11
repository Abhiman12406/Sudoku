import pytest
from src.domain.models import AllocatedSignal, IOType
from src.ui.components.cabinet_visualizer import (
    build_rack_grid_data,
    get_cable_color_map,
    render_din_rail_html,
)


def test_build_rack_grid_data():
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
            is_spare=False,
        ),
        AllocatedSignal(
            tag="WIRED SPARE",
            io_type=IOType.SPARE,
            cioc=1,
            baseplate=1,
            slot=2,
            cable_id="CBL-01",
            pair_no=2,
            is_spare=True,
        ),
    ]

    grid = build_rack_grid_data(allocations, charms_per_baseplate=12)

    assert 1 in grid  # CIOC 1
    assert 1 in grid[1]  # Baseplate 1
    bp1_slots = grid[1][1]
    assert len(bp1_slots) == 12  # All 12 physical slots present

    slot1 = bp1_slots[0]
    assert slot1["slot"] == 1
    assert slot1["tag"] == "10-FT-101"
    assert slot1["cable_id"] == "CBL-01"
    assert slot1["pair_no"] == 1
    assert not slot1["is_spare"]

    slot2 = bp1_slots[1]
    assert slot2["slot"] == 2
    assert slot2["tag"] == "WIRED SPARE"
    assert slot2["pair_no"] == 2
    assert slot2["is_spare"]

    slot3 = bp1_slots[2]
    assert slot3["slot"] == 3
    assert slot3["is_empty"]


def test_get_cable_color_map():
    allocations = [
        AllocatedSignal(tag="S1", io_type=IOType.AI, baseplate=1, slot=1, cable_id="CBL-01"),
        AllocatedSignal(tag="S2", io_type=IOType.AI, baseplate=1, slot=2, cable_id="CBL-02"),
    ]
    color_map = get_cable_color_map(allocations)
    assert "CBL-01" in color_map
    assert "CBL-02" in color_map
    assert color_map["CBL-01"] != color_map["CBL-02"]


def test_render_din_rail_html():
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
            tag="WIRED SPARE",
            io_type=IOType.SPARE,
            cioc=1,
            baseplate=1,
            slot=2,
            cable_id="CBL-01",
            pair_no=2,
            is_spare=True,
        ),
    ]

    html = render_din_rail_html(allocations)
    assert "CBL-01" in html
    assert "10-FT-101" in html
    assert "WIRED SPARE" in html
    assert "Pair 1" in html or "P01" in html or "Pair 01" in html or "P1" in html
