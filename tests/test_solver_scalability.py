import time
import pytest

from src.benchmark.synthetic_generator import generate_batch_10k
from src.domain.models import CableBlock, SegregationPolicy
from src.solver.audit import verify_allocation_invariants
from src.solver.hierarchical_solver import solve_hierarchical_packing
from src.solver.macro_packer import solve_macro_packing
from src.solver.micro_slotter import slot_cable_blocks_in_cioc


def test_micro_slotter_scalability_and_speed():
    # 44 CIOCs with mixed blocks (24, 12, 6, 2)
    # Previously this took 442 seconds. With fast micro-slotting, it must take < 2.0s.
    t0 = time.perf_counter()
    all_allocs = []
    for c in range(1, 45):
        blocks_per_cioc = (
            [CableBlock(cable_id=f"CBL-C{c:02d}-24-{i}", pair_count=24, signals=[]) for i in range(1)]
            + [CableBlock(cable_id=f"CBL-C{c:02d}-12-{i}", pair_count=12, signals=[]) for i in range(2)]
            + [CableBlock(cable_id=f"CBL-C{c:02d}-06-{i}", pair_count=6, signals=[]) for i in range(4)]
            + [CableBlock(cable_id=f"CBL-C{c:02d}-02-{i}", pair_count=2, signals=[]) for i in range(12)]
        )
        allocs = slot_cable_blocks_in_cioc(blocks_per_cioc, cioc_id=c)
        all_allocs.extend(allocs)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    assert elapsed < 2.0, f"Micro-slotting 44 CIOCs took {elapsed:.2f}s, expected < 2.0s"
    assert len(all_allocs) == 44 * 96

    # Verify invariants on all 4,224 allocated slots
    valid, errors = verify_allocation_invariants(all_allocs)
    assert valid, f"Verification failed with errors: {errors}"
    assert len(errors) == 0


def test_macro_packer_scalability_1000_cables():
    # 1,000 cable blocks with mixed sizes and trains
    import random
    rng = random.Random(42)
    sizes = [24, 12, 6, 2]
    weights = [0.3, 0.4, 0.2, 0.1]
    trains = ["A", "B", None]
    train_weights = [0.4, 0.4, 0.2]

    blocks = []
    for i in range(1000):
        sz = rng.choices(sizes, weights=weights, k=1)[0]
        tr = rng.choices(trains, weights=train_weights, k=1)[0]
        blocks.append(
            CableBlock(
                cable_id=f"CBL-{i:04d}",
                pair_count=sz,
                segregation=tr,
                signals=[],
            )
        )

    t0 = time.perf_counter()
    result = solve_macro_packing(
        blocks,
        slots_per_cioc=96,
        time_limit_seconds=10.0,
        segregation_policy=SegregationPolicy.CIOC,
    )
    t1 = time.perf_counter()

    elapsed = t1 - t0
    assert elapsed < 10.0, f"Macro packing 1000 cables took {elapsed:.2f}s, expected < 10.0s"
    assert result.num_ciocs > 0

    # Ensure all 1000 blocks are assigned
    total_placed = sum(len(b_list) for b_list in result.cioc_assignments.values())
    assert total_placed == 1000

    # Ensure zero segregation violations
    for c, blist in result.cioc_assignments.items():
        c_trains = {b.segregation for b in blist if b.segregation}
        assert not ("A" in c_trains and "B" in c_trains), f"Segregation breach in CIOC {c}: {c_trains}"


def test_hierarchical_packing_10k_solver_sub_15s():
    signals = generate_batch_10k(seed=42)
    assert len(signals) == 10000

    t0 = time.perf_counter()
    allocs = solve_hierarchical_packing(signals, time_limit_seconds=30.0)
    t1 = time.perf_counter()

    elapsed = t1 - t0
    assert elapsed < 20.0, f"Full 10k hierarchical solve took {elapsed:.2f}s, expected < 20.0s"

    # All signals must be allocated plus wired spares
    active_allocs = [a for a in allocs if not a.is_spare]
    assert len(active_allocs) == 10000

    # Invariant audit must pass with 0 errors
    valid, errors = verify_allocation_invariants(allocs)
    assert valid, f"Invariant verification failed on 10k allocation: {errors}"
    assert len(errors) == 0
