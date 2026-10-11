"""Stage 1 Macro CIOC Packing Solver using Google OR-Tools CP-SAT."""

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Sequence, Union
from ortools.sat.python import cp_model

from src.domain.models import CableBlock, SegregationPolicy


@dataclass
class MacroPackingResult:
    """Outcome of Stage 1 macro-packing solver."""
    cioc_assignments: Dict[int, List[CableBlock]] = field(default_factory=dict)
    num_ciocs: int = 0
    total_slots_used: Dict[int, int] = field(default_factory=dict)
    cioc_trains: Dict[int, Optional[str]] = field(default_factory=dict)


def solve_macro_packing(
    cable_blocks: Sequence[CableBlock],
    slots_per_cioc: int = 96,
    spare_margin: float = 0.0,
    time_limit_seconds: float = 10.0,
    segregation_policy: Union[str, SegregationPolicy] = SegregationPolicy.CIOC,
    ciocs_per_cabinet: int = 4,
) -> MacroPackingResult:
    """Assign CableBlocks to CIOC containers using CP-SAT bin-packing.

    Args:
        cable_blocks: Sequence of CableBlock domain bundles.
        slots_per_cioc: Max slots (channels) per CIOC card (default: 8 * 12 = 96).
        spare_margin: Percentage of slots to keep empty as reserve (e.g. 0.1 for 10%).
        time_limit_seconds: Solver max execution time in seconds.
        segregation_policy: "CIOC" (CIOC-level segregation) or "CABINET" (Cabinet-level segregation).
        ciocs_per_cabinet: Number of CIOCs per Marshalling Cabinet (default: 4).

    Returns:
        MacroPackingResult with mapping of CIOC index (1..N) to assigned cable blocks and train metadata.
    """
    if not cable_blocks:
        return MacroPackingResult()

    policy = (
        SegregationPolicy.from_str(segregation_policy)
        if isinstance(segregation_policy, str)
        else segregation_policy
    )

    eff_capacity = int(math.floor(slots_per_cioc * (1.0 - spare_margin)))
    if eff_capacity < 1:
        raise ValueError(f"Effective capacity {eff_capacity} must be at least 1")

    # Validate that no single cable block exceeds CIOC capacity
    for block in cable_blocks:
        if block.pair_count > eff_capacity:
            raise ValueError(
                f"Cable '{block.cable_id}' requires {block.pair_count} slots, exceeding CIOC capacity {eff_capacity}"
            )

    has_train_a = any(b.segregation == "A" for b in cable_blocks)
    has_train_b = any(b.segregation == "B" for b in cable_blocks)
    has_segregation = has_train_a and has_train_b

    num_blocks = len(cable_blocks)

    if policy == SegregationPolicy.CABINET and has_segregation:
        num_cabs = max(2, num_blocks)
        max_ciocs = num_cabs * ciocs_per_cabinet
    else:
        max_ciocs = num_blocks

    max_cabs = math.ceil(max_ciocs / ciocs_per_cabinet)

    model = cp_model.CpModel()

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

    # Constraint 2: Capacity constraint for each CIOC & linking
    for c in range(1, max_ciocs + 1):
        block_slots_in_c = sum(cable_blocks[k].pair_count * y[k, c] for k in range(num_blocks))
        model.Add(block_slots_in_c <= eff_capacity * u[c])
        for k in range(num_blocks):
            model.Add(u[c] >= y[k, c])

    # Constraint 3: Linearized Indicator Redundancy Cuts at CIOC level
    a_blocks = [k for k in range(num_blocks) if cable_blocks[k].segregation == "A"]
    b_blocks = [k for k in range(num_blocks) if cable_blocks[k].segregation == "B"]

    for c in range(1, max_ciocs + 1):
        for k in a_blocks:
            model.Add(u_a[c] >= y[k, c])
        if a_blocks:
            model.Add(u_a[c] <= sum(y[k, c] for k in a_blocks))
        else:
            model.Add(u_a[c] == 0)

        for k in b_blocks:
            model.Add(u_b[c] >= y[k, c])
        if b_blocks:
            model.Add(u_b[c] <= sum(y[k, c] for k in b_blocks))
        else:
            model.Add(u_b[c] == 0)

        # Train A and Train B never share the same CIOC: U_c^A + U_c^B <= 1
        model.Add(u_a[c] + u_b[c] <= 1)

    # Constraint 4: Cabinet-Level Redundancy Cuts (if policy is CABINET)
    u_cab = {}
    u_cab_a = {}
    u_cab_b = {}

    for cab in range(1, max_cabs + 1):
        u_cab[cab] = model.NewBoolVar(f"cab_used_{cab}")
        u_cab_a[cab] = model.NewBoolVar(f"cab_train_a_{cab}")
        u_cab_b[cab] = model.NewBoolVar(f"cab_train_b_{cab}")

        # CIOCs in cabinet cab:
        cab_ciocs = [
            c for c in range(1, max_ciocs + 1)
            if (c - 1) // ciocs_per_cabinet + 1 == cab
        ]
        for c in cab_ciocs:
            model.Add(u_cab[cab] >= u[c])
            model.Add(u_cab_a[cab] >= u_a[c])
            model.Add(u_cab_b[cab] >= u_b[c])

        if cab_ciocs:
            model.Add(u_cab_a[cab] <= sum(u_a[c] for c in cab_ciocs))
            model.Add(u_cab_b[cab] <= sum(u_b[c] for c in cab_ciocs))
            model.Add(u_cab[cab] <= sum(u[c] for c in cab_ciocs))
        else:
            model.Add(u_cab_a[cab] == 0)
            model.Add(u_cab_b[cab] == 0)
            model.Add(u_cab[cab] == 0)

        if policy == SegregationPolicy.CABINET and has_segregation:
            # Linear indicator cut at Cabinet level: U_cab^A + U_cab^B <= 1
            model.Add(u_cab_a[cab] + u_cab_b[cab] <= 1)

    # Symmetry breaking and Objective formulation
    if policy == SegregationPolicy.CABINET and has_segregation:
        # Symmetry breaking across cabinets
        for cab in range(1, max_cabs):
            model.Add(u_cab[cab] >= u_cab[cab + 1])

        # Symmetry breaking within each cabinet
        for cab in range(1, max_cabs + 1):
            cab_ciocs = [
                c for c in range(1, max_ciocs + 1)
                if (c - 1) // ciocs_per_cabinet + 1 == cab
            ]
            for i in range(len(cab_ciocs) - 1):
                c_curr = cab_ciocs[i]
                c_next = cab_ciocs[i + 1]
                model.Add(u[c_curr] >= u[c_next])

        model.Minimize(
            sum(10000 * u_cab[cab] for cab in range(1, max_cabs + 1))
            + sum(1000 * u[c] for c in range(1, max_ciocs + 1))
            + sum(c * y[k, c] for k in range(num_blocks) for c in range(1, max_ciocs + 1))
        )
    else:
        # Standard CIOC symmetry breaking
        for c in range(1, max_ciocs):
            model.Add(u[c] >= u[c + 1])

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

    # Determine train metadata for each active CIOC
    cioc_trains: Dict[int, Optional[str]] = {}
    for c, blocks in cioc_assignments.items():
        trains_in_c = {b.segregation for b in blocks if b.segregation}
        if "A" in trains_in_c and "B" in trains_in_c:
            cioc_trains[c] = "MIXED"
        elif "A" in trains_in_c:
            cioc_trains[c] = "A"
        elif "B" in trains_in_c:
            cioc_trains[c] = "B"
        else:
            cioc_trains[c] = None

    return MacroPackingResult(
        cioc_assignments=cioc_assignments,
        num_ciocs=len(active_ciocs),
        total_slots_used=total_slots_used,
        cioc_trains=cioc_trains,
    )
