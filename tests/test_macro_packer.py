import pytest
from src.domain.models import CableBlock, Signal, IOType
from src.solver.macro_packer import solve_macro_packing, MacroPackingResult


def test_macro_packing_single_cioc():
    # 4 cables of 12 pairs each = 48 slots <= 96 slots -> 1 CIOC
    blocks = [
        CableBlock(cable_id=f"CBL-{i:02d}", pair_count=12, signals=[])
        for i in range(1, 5)
    ]
    result = solve_macro_packing(blocks, slots_per_cioc=96)

    assert result.num_ciocs == 1
    assert 1 in result.cioc_assignments
    assert len(result.cioc_assignments[1]) == 4
    assert result.total_slots_used[1] == 48


def test_macro_packing_multiple_ciocs_overflow():
    # 5 cables of 24 pairs = 120 slots > 96 slots -> must use at least 2 CIOCs
    blocks = [
        CableBlock(cable_id=f"CBL-24-{i:02d}", pair_count=24, signals=[])
        for i in range(1, 6)
    ]
    result = solve_macro_packing(blocks, slots_per_cioc=96)

    assert result.num_ciocs == 2
    # Verify no CIOC exceeds 96 slots
    for cioc_id, used_slots in result.total_slots_used.items():
        assert used_slots <= 96

    # Verify all 5 cables are placed exactly once
    assigned_cables = []
    for c_list in result.cioc_assignments.values():
        assigned_cables.extend([b.cable_id for b in c_list])
    assert sorted(assigned_cables) == sorted([b.cable_id for b in blocks])


def test_macro_packing_empty():
    result = solve_macro_packing([], slots_per_cioc=96)
    assert result.num_ciocs == 0
    assert result.cioc_assignments == {}
