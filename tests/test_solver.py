import pytest
from src.domain.models import IOType, Signal, AllocatedSignal
from src.solver.walking_solver import solve_walking_skeleton


def test_solve_single_cable_within_capacity():
    signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1, description="Flow Transmitter"),
        Signal(tag="10-FV-101", io_type=IOType.AO, cable_id="CBL-01", pair_no=2, description="Flow Valve"),
        Signal(tag="10-PSH-102", io_type=IOType.DI, cable_id="CBL-01", pair_no=3, description="Pressure Switch"),
        Signal(tag="10-XV-102", io_type=IOType.DO, cable_id="CBL-01", pair_no=4, description="Solenoid Valve"),
    ]

    allocations = solve_walking_skeleton(signals, charms_per_baseplate=12)

    assert len(allocations) == 4
    # All should fit on Baseplate 1
    for alloc in allocations:
        assert alloc.baseplate == 1
        assert 1 <= alloc.slot <= 12

    # Slots must be distinct
    slots = [a.slot for a in allocations]
    assert len(set(slots)) == len(slots)

    # Ascending pair order preserved
    alloc_map = {a.tag: a for a in allocations}
    assert alloc_map["10-FT-101"].slot < alloc_map["10-FV-101"].slot
    assert alloc_map["10-FV-101"].slot < alloc_map["10-PSH-102"].slot
    assert alloc_map["10-PSH-102"].slot < alloc_map["10-XV-102"].slot

    # CHARM and Terminal block assignments
    assert alloc_map["10-FT-101"].charm_part_no == "KL3001X1-BA1"
    assert alloc_map["10-FT-101"].terminal_block_type == "Standard"
    assert alloc_map["10-XV-102"].charm_part_no == "KL3004X1-BA1"
    assert alloc_map["10-XV-102"].terminal_block_type == "Fused Injected-Power"


def test_solve_signals_spanning_multiple_baseplates():
    # 15 signals, charms_per_baseplate=12 -> must span 2 baseplates
    signals = [
        Signal(tag=f"TAG-{i:02d}", io_type=IOType.AI, cable_id="CBL-01", pair_no=i)
        for i in range(1, 16)
    ]

    allocations = solve_walking_skeleton(signals, charms_per_baseplate=12)

    assert len(allocations) == 15

    # Check capacity invariant: no baseplate has more than 12
    bp_counts = {}
    for a in allocations:
        bp_counts[a.baseplate] = bp_counts.get(a.baseplate, 0) + 1
        assert 1 <= a.slot <= 12

    for bp, count in bp_counts.items():
        assert count <= 12

    # Check distinct coordinates (baseplate, slot)
    coords = [(a.baseplate, a.slot) for a in allocations]
    assert len(set(coords)) == 15


def test_solve_empty_signals():
    allocations = solve_walking_skeleton([], charms_per_baseplate=12)
    assert allocations == []
