import pytest
from src.domain.models import IOType, Signal, AllocatedSignal
from src.solver.audit import verify_allocation_invariants
from src.solver.hierarchical_solver import solve_hierarchical_packing


def test_hierarchical_packing_mixed_cables_audit_passes():
    # 1 x 24-pair cable (with 20 active signals, 4 wired spares)
    # 2 x 12-pair cables (one full 12, one with 10 active signals)
    # 2 x 6-pair cables
    # 1 x 2-pair cable
    signals = []

    # 24-pair cable
    for i in range(1, 21):
        signals.append(
            Signal(tag=f"24P-SIG-{i:02d}", io_type=IOType.AI, cable_id="CBL-24P", pair_no=i)
        )

    # 12-pair cable full
    for i in range(1, 13):
        signals.append(
            Signal(tag=f"12P-A-SIG-{i:02d}", io_type=IOType.AO, cable_id="CBL-12P-A", pair_no=i)
        )

    # 12-pair cable sparse
    for i in range(1, 11):
        signals.append(
            Signal(tag=f"12P-B-SIG-{i:02d}", io_type=IOType.DI, cable_id="CBL-12P-B", pair_no=i)
        )

    # Two 6-pair cables
    for i in range(1, 7):
        signals.append(
            Signal(tag=f"6P-A-SIG-{i:02d}", io_type=IOType.DO, cable_id="CBL-6P-A", pair_no=i)
        )
    for i in range(1, 5):
        signals.append(
            Signal(tag=f"6P-B-SIG-{i:02d}", io_type=IOType.TC, cable_id="CBL-6P-B", pair_no=i)
        )

    # One 2-pair cable
    signals.append(
        Signal(tag="2P-SIG-01", io_type=IOType.RTD, cable_id="CBL-2P", pair_no=1)
    )

    # Total cable channels = 24 + 12 + 12 + 6 + 6 + 2 = 62 <= 96 slots -> fits in 1 CIOC
    allocations = solve_hierarchical_packing(signals)

    # Verify total allocated slots equals sum of cable pair capacities = 62
    assert len(allocations) == 62

    # Audit pass must pass with 0 errors
    valid, errors = verify_allocation_invariants(allocations)
    assert valid, f"Verification failed with errors: {errors}"
    assert len(errors) == 0

    # Check wired spares existence
    spares = [a for a in allocations if a.is_spare]
    # CBL-24P: 4 spares (pairs 21..24)
    # CBL-12P-B: 2 spares (pairs 11..12)
    # CBL-6P-B: 2 spares (pairs 5..6)
    # CBL-2P: 1 spare (pair 2)
    # Total = 4 + 2 + 2 + 1 = 9 spares
    assert len(spares) == 9
    for s in spares:
        assert s.tag == "WIRED SPARE"
        assert s.io_type == IOType.SPARE
        assert s.charm_part_no is None


def test_hierarchical_packing_multiple_ciocs():
    # 5 x 24-pair cables = 120 channels -> spans 2 CIOCs
    signals = []
    for c_idx in range(1, 6):
        cid = f"CBL-TRUNK-{c_idx:02d}"
        for p in range(1, 23):  # 22 active signals per cable
            signals.append(
                Signal(tag=f"SIG-C{c_idx}-P{p:02d}", io_type=IOType.AI, cable_id=cid, pair_no=p)
            )

    allocations = solve_hierarchical_packing(signals)

    assert len(allocations) == 5 * 24  # 120 total allocated channels
    ciocs_used = {a.cioc for a in allocations}
    assert ciocs_used == {1, 2}

    valid, errors = verify_allocation_invariants(allocations)
    assert valid, f"Verification failed with errors: {errors}"
    assert len(errors) == 0


def test_audit_detects_shuffled_pairs():
    # Deliberately construct an allocation with inverted pair order
    allocations = [
        AllocatedSignal(
            tag="SIG-01",
            io_type=IOType.AI,
            baseplate=1,
            slot=1,
            cioc=1,
            cable_id="CBL-01",
            pair_no=2,  # Shuffled! Pair 2 at slot 1
        ),
        AllocatedSignal(
            tag="SIG-02",
            io_type=IOType.AI,
            baseplate=1,
            slot=2,
            cioc=1,
            cable_id="CBL-01",
            pair_no=1,  # Shuffled! Pair 1 at slot 2
        ),
    ]

    valid, errors = verify_allocation_invariants(allocations)
    assert not valid
    assert any("pair" in e.lower() for e in errors)


def test_audit_detects_fragmented_cable():
    # Deliberately construct an allocation with non-contiguous slots for same cable
    allocations = [
        AllocatedSignal(
            tag="SIG-01",
            io_type=IOType.AI,
            baseplate=1,
            slot=1,
            cioc=1,
            cable_id="CBL-01",
            pair_no=1,
        ),
        AllocatedSignal(
            tag="SIG-02",
            io_type=IOType.AI,
            baseplate=1,
            slot=5,  # Gapped! Slot 5 instead of 2
            cioc=1,
            cable_id="CBL-01",
            pair_no=2,
        ),
    ]

    valid, errors = verify_allocation_invariants(allocations)
    assert not valid
    assert any("contiguous" in e.lower() for e in errors)
