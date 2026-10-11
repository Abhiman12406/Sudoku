import pytest
from src.domain.models import CableBlock, Signal, IOType, AllocatedSignal
from src.solver.micro_slotter import slot_cable_blocks_in_cioc


def test_24_pair_cable_spans_two_baseplates_with_wired_spares():
    # 24-pair cable with 22 active signals and 2 unused pairs (23, 24)
    signals = [
        Signal(
            tag=f"10-TT-{i:02d}",
            io_type=IOType.AI,
            cable_id="CBL-TRUNK-24",
            pair_no=i,
            description=f"Temperature Transmitter {i}",
        )
        for i in range(1, 23)
    ]
    block = CableBlock(
        cable_id="CBL-TRUNK-24",
        pair_count=24,
        signals=signals,
    )

    allocations = slot_cable_blocks_in_cioc([block], cioc_id=1, baseplates_per_cioc=8)

    # Must allocate all 24 slots (22 signals + 2 wired spares)
    assert len(allocations) == 24

    # Group by baseplate
    bp1 = [a for a in allocations if a.baseplate == 1]
    bp2 = [a for a in allocations if a.baseplate == 2]

    assert len(bp1) == 12
    assert len(bp2) == 12

    # Check Baseplate 1: pairs 1..12 in slots 1..12
    for slot_idx, alloc in enumerate(bp1, start=1):
        assert alloc.slot == slot_idx
        assert alloc.pair_no == slot_idx
        assert alloc.tag == f"10-TT-{slot_idx:02d}"
        assert not alloc.is_spare

    # Check Baseplate 2: pairs 13..22 active, 23..24 wired spares
    for slot_idx, alloc in enumerate(bp2, start=1):
        pair = slot_idx + 12
        assert alloc.slot == slot_idx
        assert alloc.pair_no == pair
        if pair <= 22:
            assert alloc.tag == f"10-TT-{pair:02d}"
            assert not alloc.is_spare
        else:
            assert alloc.tag == "WIRED SPARE"
            assert alloc.is_spare
            assert alloc.io_type == IOType.SPARE


def test_12_pair_cable_spans_one_baseplate_with_wired_spares():
    # 12-pair cable with 8 active signals
    signals = [
        Signal(
            tag=f"10-PT-{i:02d}",
            io_type=IOType.AI,
            cable_id="CBL-TRUNK-12",
            pair_no=i,
        )
        for i in range(1, 9)
    ]
    block = CableBlock(
        cable_id="CBL-TRUNK-12",
        pair_count=12,
        signals=signals,
    )

    allocations = slot_cable_blocks_in_cioc([block], cioc_id=1, baseplates_per_cioc=8)

    assert len(allocations) == 12
    # All 12 slots must be on Baseplate 1
    for alloc in allocations:
        assert alloc.baseplate == 1

    # Slots 1..8 are active signals, 9..12 are wired spares
    for slot_idx, alloc in enumerate(allocations, start=1):
        assert alloc.slot == slot_idx
        assert alloc.pair_no == slot_idx
        if slot_idx <= 8:
            assert alloc.tag == f"10-PT-{slot_idx:02d}"
            assert not alloc.is_spare
        else:
            assert alloc.tag == "WIRED SPARE"
            assert alloc.is_spare
            assert alloc.io_type == IOType.SPARE


def test_two_6_pair_cables_fit_on_single_baseplate():
    # Two 6-pair cables should pack onto baseplate 1 (slots 1..6 and 7..12)
    sig_a = [Signal(tag=f"TAG-A-{i}", io_type=IOType.AI, cable_id="CBL-A", pair_no=i) for i in range(1, 7)]
    sig_b = [Signal(tag=f"TAG-B-{i}", io_type=IOType.AI, cable_id="CBL-B", pair_no=i) for i in range(1, 7)]

    block_a = CableBlock(cable_id="CBL-A", pair_count=6, signals=sig_a)
    block_b = CableBlock(cable_id="CBL-B", pair_count=6, signals=sig_b)

    allocations = slot_cable_blocks_in_cioc([block_a, block_b], cioc_id=1, baseplates_per_cioc=8)

    assert len(allocations) == 12
    # All on baseplate 1
    assert all(a.baseplate == 1 for a in allocations)

    # Slots 1..12 must all be covered without overlap
    slots = [a.slot for a in allocations]
    assert sorted(slots) == list(range(1, 13))

    # Cable A and Cable B must each have contiguous slots
    slots_a = [a.slot for a in allocations if a.cable_id == "CBL-A"]
    slots_b = [a.slot for a in allocations if a.cable_id == "CBL-B"]
    assert slots_a == list(range(min(slots_a), max(slots_a) + 1))
    assert slots_b == list(range(min(slots_b), max(slots_b) + 1))


def test_micro_slotting_custom_baseplate_capacity():
    # Verify that micro slotter handles charms_per_baseplate < 12 without IndexError
    sig_2 = [Signal(tag=f"TAG-2P-{i}", io_type=IOType.AI, cable_id="CBL-2P", pair_no=i) for i in range(1, 3)]
    block_2 = CableBlock(cable_id="CBL-2P", pair_count=2, signals=sig_2)

    allocations = slot_cable_blocks_in_cioc(
        [block_2],
        cioc_id=1,
        baseplates_per_cioc=4,
        charms_per_baseplate=6,
    )
    assert len(allocations) == 2
    assert all(a.baseplate == 1 for a in allocations)
    assert [a.slot for a in allocations] == [1, 2]

