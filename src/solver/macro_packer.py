"""Stage 1 Macro CIOC Packing Solver using Google OR-Tools CP-SAT."""

from dataclasses import dataclass, field
import math
from typing import Dict, List, Sequence
from ortools.sat.python import cp_model

from src.domain.models import CableBlock


@dataclass
class MacroPackingResult:
    """Outcome of Stage 1 macro-packing solver."""
    cioc_assignments: Dict[int, List[CableBlock]] = field(default_factory=dict)
    num_ciocs: int = 0
    total_slots_used: Dict[int, int] = field(default_factory=dict)


def solve_macro_packing(
    cable_blocks: Sequence[CableBlock],
    slots_per_cioc: int = 96,
    spare_margin: float = 0.0,
    time_limit_seconds: float = 10.0,
) -> MacroPackingResult:
    """Assign CableBlocks to CIOC containers using CP-SAT bin-packing.

    Args:
        cable_blocks: Sequence of CableBlock domain bundles.
        slots_per_cioc: Max slots (channels) per CIOC card (default: 8 * 12 = 96).
        spare_margin: Percentage of slots to keep empty as reserve (e.g. 0.1 for 10%).
        time_limit_seconds: Solver max execution time in seconds.

    Returns:
        MacroPackingResult with mapping of CIOC index (1..N) to assigned cable blocks.
    """
    if not cable_blocks:
        return MacroPackingResult()

    eff_capacity = int(math.floor(slots_per_cioc * (1.0 - spare_margin)))
    if eff_capacity < 1:
        raise ValueError(f"Effective capacity {eff_capacity} must be at least 1")

    # Validate that no single cable block exceeds CIOC capacity
    for block in cable_blocks:
        if block.pair_count > eff_capacity:
            raise ValueError(
                f"Cable '{block.cable_id}' requires {block.pair_count} slots, exceeding CIOC capacity {eff_capacity}"
            )

    total_pairs = sum(b.pair_count for b in cable_blocks)
    lower_bound_ciocs = max(1, math.ceil(total_pairs / eff_capacity))
    max_ciocs = len(cable_blocks)

    model = cp_model.CpModel()

    num_blocks = len(cable_blocks)
    y = {}  # y[k, c] in {0, 1}
    u = {}  # u[c] in {0, 1} indicator that CIOC c is used
    u_a = {}  # Train A indicator per CIOC
    u_b = {}  # Train B indicator per CIOC

    for c in range(1, max_ciocs + 1):
        u[c] = model.NewBoolVar(f"cioc_used_{c}")
        u_a[c] = model.NewBoolVar(f"cioc_train_a_{c}")
        u_b[c] = model.NewBoolVar(f"cioc_train_b_{c}")

    for k in range(num_blocks):
        for c in range(1, max_ciocs + 1):
            y[k, c] = model.NewBoolVar(f"assign_{k}_{c}")

    # Constraint 1: Every cable block must be assigned to exactly one CIOC
    for k in range(num_blocks):
        model.Add(sum(y[k, c] for c in range(1, max_ciocs + 1)) == 1)

    # Constraint 2: Capacity constraint for each CIOC
    for c in range(1, max_ciocs + 1):
        block_slots_in_c = sum(cable_blocks[k].pair_count * y[k, c] for k in range(num_blocks))
        model.Add(block_slots_in_c <= eff_capacity * u[c])
        # Linking: if any block is in c, u[c] must be 1
        for k in range(num_blocks):
            model.Add(u[c] >= y[k, c])

    # Constraint 3: Linearized Indicator Redundancy Cuts (Train A / Train B mutual exclusion)
    has_segregation = any(b.segregation in ("A", "B") for b in cable_blocks)
    if has_segregation:
        for c in range(1, max_ciocs + 1):
            for k in range(num_blocks):
                if cable_blocks[k].segregation == "A":
                    model.Add(u_a[c] >= y[k, c])
                elif cable_blocks[k].segregation == "B":
                    model.Add(u_b[c] >= y[k, c])
            # Train A and Train B never share the same CIOC: U_c^A + U_c^B <= 1
            model.Add(u_a[c] + u_b[c] <= 1)


    # Symmetry breaking: u[1] >= u[2] >= ... >= u[max_ciocs]
    for c in range(1, max_ciocs):
        model.Add(u[c] >= u[c + 1])

    # Objective: Minimize activated CIOCs and pack earlier CIOCs tightly
    model.Minimize(
        sum(1000 * u[c] for c in range(1, max_ciocs + 1))
        + sum(c * y[k, c] for k in range(num_blocks) for c in range(1, max_ciocs + 1))
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Stage 1 macro-packing solver failed with status {solver.StatusName(status)}")

    cioc_assignments: Dict[int, List[CableBlock]] = {}
    total_slots_used: Dict[int, int] = {}
    active_ciocs = set()

    for k, block in enumerate(cable_blocks):
        assigned_c = None
        for c in range(1, max_ciocs + 1):
            if solver.Value(y[k, c]) == 1:
                assigned_c = c
                break
        if assigned_c is None:
            raise RuntimeError(f"Cable {block.cable_id} was not assigned to any CIOC")

        active_ciocs.add(assigned_c)
        if assigned_c not in cioc_assignments:
            cioc_assignments[assigned_c] = []
            total_slots_used[assigned_c] = 0
        cioc_assignments[assigned_c].append(block)
        total_slots_used[assigned_c] += block.pair_count

    # Sort blocks within each CIOC deterministically by cable_id
    for c in cioc_assignments:
        cioc_assignments[c].sort(key=lambda b: b.cable_id)

    return MacroPackingResult(
        cioc_assignments=cioc_assignments,
        num_ciocs=len(active_ciocs),
        total_slots_used=total_slots_used,
    )
