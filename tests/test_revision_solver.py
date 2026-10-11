"""Unit tests for Seam 2: Revision Perturbation & Freezing Solver."""

import pytest
from src.domain.models import AllocatedSignal, IOType, Signal
from src.revision.classifier import classify_revision_diff
from src.revision.solver import RevisionAllocationResult, solve_revision_allocation


def test_unchanged_signals_are_frozen_at_delta_zero():
    rev_a_allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=1,
            cable_id="CBL-01",
            pair_no=1,
        ),
        AllocatedSignal(
            tag="10-PT-102",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=2,
            cable_id="CBL-01",
            pair_no=2,
        ),
        AllocatedSignal(
            tag="10-TT-103",
            io_type=IOType.RTD,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=3,
            cable_id="CBL-01",
            pair_no=3,
        ),
    ]

    rev_b_signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1),
        Signal(tag="10-PT-102", io_type=IOType.AI, cable_id="CBL-01", pair_no=2),
        Signal(tag="10-TT-103", io_type=IOType.RTD, cable_id="CBL-01", pair_no=3),
    ]

    result = solve_revision_allocation(rev_a_allocations, rev_b_signals)

    assert isinstance(result, RevisionAllocationResult)
    assert len(result.allocations) == 3
    assert result.perturbation_score == 0
    assert len(result.moved_signals) == 0

    # Verify physical slots are identically frozen
    alloc_map = {a.tag: a for a in result.allocations}
    for orig in rev_a_allocations:
        b_alloc = alloc_map[orig.tag]
        assert (b_alloc.cabinet, b_alloc.cioc, b_alloc.baseplate, b_alloc.slot) == (
            orig.cabinet,
            orig.cioc,
            orig.baseplate,
            orig.slot,
        )


def test_deleted_signal_slot_is_backfilled_by_added_signal():
    rev_a_allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=1,
        ),
        AllocatedSignal(
            tag="10-PT-102",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=2,
        ),
        AllocatedSignal(
            tag="10-TT-103",
            io_type=IOType.RTD,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=3,
        ),
    ]

    # Rev B deletes PT-102 (slot 2 vacated) and adds new signal LT-104
    rev_b_signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI),
        Signal(tag="10-TT-103", io_type=IOType.RTD),
        Signal(tag="10-LT-104", io_type=IOType.AI),
    ]

    result = solve_revision_allocation(rev_a_allocations, rev_b_signals)

    alloc_map = {a.tag: a for a in result.allocations}
    # 10-FT-101 and 10-TT-103 are frozen in slot 1 and 3
    assert alloc_map["10-FT-101"].slot == 1
    assert alloc_map["10-TT-103"].slot == 3

    # 10-LT-104 backfills vacated slot 2!
    assert alloc_map["10-LT-104"].slot == 2
    assert alloc_map["10-LT-104"].baseplate == 1
    assert alloc_map["10-LT-104"].cioc == 1
    assert (1, 1, 2) in result.backfilled_slots


def test_modified_signal_io_type_change_stays_in_same_slot():
    rev_a_allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=1,
        ),
    ]

    # Rev B modifies IO type from AI to AO
    rev_b_signals = [
        Signal(tag="10-FT-101", io_type=IOType.AO),
    ]

    result = solve_revision_allocation(rev_a_allocations, rev_b_signals)

    assert len(result.allocations) == 1
    res = result.allocations[0]
    assert res.tag == "10-FT-101"
    assert res.io_type == IOType.AO
    assert res.slot == 1  # exact same slot preserved
    assert res.baseplate == 1
    assert res.cioc == 1
    assert result.perturbation_score == 0
    assert "Analog Output" in (res.charm_model or "")
    assert res.charm_part_no == "KL3002X1-BA1"


def test_modified_signal_segregation_change_moves_to_separate_cioc():
    # In Rev A, FT-101 was Train A on CIOC 1, slot 1. PT-102 was also Train A on CIOC 1, slot 2.
    rev_a_allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=1,
            segregation="A",
        ),
        AllocatedSignal(
            tag="10-PT-102",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=2,
            segregation="A",
        ),
    ]

    # In Rev B, 10-FT-101 remains unchanged (Train A).
    # 10-PT-102 is modified to Train B!
    rev_b_signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI, segregation="A"),
        Signal(tag="10-PT-102", io_type=IOType.AI, segregation="B"),
    ]

    result = solve_revision_allocation(rev_a_allocations, rev_b_signals)

    alloc_map = {a.tag: a for a in result.allocations}
    # FT-101 is frozen on CIOC 1, slot 1
    assert alloc_map["10-FT-101"].cioc == 1
    assert alloc_map["10-FT-101"].slot == 1

    # PT-102 cannot stay on CIOC 1 because of Train A / Train B segregation!
    # It must move to CIOC 2 (same cabinet)
    assert alloc_map["10-PT-102"].cioc != 1
    assert alloc_map["10-PT-102"].cabinet == 1  # stays in same cabinet to minimize delta!
    assert result.perturbation_score > 0
    assert len(result.moved_signals) == 1
    assert result.moved_signals[0].tag == "10-PT-102"


def test_cable_contiguity_in_revision_solver():
    rev_a_allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=1,
        )
    ]
    # Rev B adds a 2-pair cable CBL-NEW with pairs 1 and 2
    rev_b_signals = [
        Signal(tag="10-FT-101", io_type=IOType.AI),
        Signal(tag="20-FT-201", io_type=IOType.AI, cable_id="CBL-NEW", pair_no=1),
        Signal(tag="20-FT-202", io_type=IOType.AI, cable_id="CBL-NEW", pair_no=2),
    ]
    result = solve_revision_allocation(rev_a_allocations, rev_b_signals)
    alloc_map = {a.tag: a for a in result.allocations}

    # FT-101 is frozen at slot 1
    assert alloc_map["10-FT-101"].slot == 1

    # Pairs 1 and 2 of CBL-NEW must land contiguously and in order on the same baseplate
    s1 = alloc_map["20-FT-201"]
    s2 = alloc_map["20-FT-202"]
    assert s1.cioc == s2.cioc
    assert s1.baseplate == s2.baseplate
    assert s2.slot == s1.slot + 1


def test_cable_contiguity_with_frozen_baseline_pair():
    from src.solver.audit import verify_allocation_invariants

    rev_a_allocations = [
        AllocatedSignal(
            tag="10-FT-101",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=1,
            cable_id="CBL-01",
            pair_no=1,
        ),
        AllocatedSignal(
            tag="10-DEL-02",
            io_type=IOType.AI,
            cabinet=1,
            cioc=1,
            baseplate=1,
            slot=10,
            cable_id="CBL-DEL",
            pair_no=1,
        ),
    ]

    rev_b_signals = [
        # 10-FT-101 is unchanged and frozen at slot 1
        Signal(tag="10-FT-101", io_type=IOType.AI, cable_id="CBL-01", pair_no=1),
        # 10-DEL-02 is deleted, so slot 10 is vacated (cost 0)
        # 10-TT-103 is added as Pair 2 of CBL-01. It must land at slot 2 next to Pair 1, NOT jump to slot 10!
        Signal(tag="10-TT-103", io_type=IOType.AI, cable_id="CBL-01", pair_no=2),
    ]

    result = solve_revision_allocation(rev_a_allocations, rev_b_signals)
    alloc_map = {a.tag: a for a in result.allocations}

    assert alloc_map["10-FT-101"].slot == 1
    assert alloc_map["10-TT-103"].slot == 2
    assert alloc_map["10-TT-103"].baseplate == 1
    assert alloc_map["10-TT-103"].cioc == 1

    valid, errors = verify_allocation_invariants(result.allocations)
    assert valid, f"Allocation invariants failed: {errors}"



