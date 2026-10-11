"""Walking skeleton CP-SAT slot assignment solver for DeltaV CHARMs."""

from typing import List, Optional, Sequence
from ortools.sat.python import cp_model

from src.domain.hardware import resolve_hardware_assignment, resolve_hardware_for_io
from src.domain.models import AllocatedSignal, Signal


def solve_walking_skeleton(
    signals: Sequence[Signal],
    charms_per_baseplate: int = 12,
    catalog: Optional[dict] = None,
) -> List[AllocatedSignal]:
    """Assign physical baseplate and slot coordinates using Google OR-Tools CP-SAT.

    Enforces:
      - At most `charms_per_baseplate` (default 12) per baseplate.
      - Slot coordinates between 1 and `charms_per_baseplate`.
      - Strict uniqueness: no two signals share the same (baseplate, slot).
      - Strict ascending pair order for signals in the same trunk cable.

    Args:
        signals: List of validated input Signal domain models.
        charms_per_baseplate: Capacity of each physical baseplate (12).
        catalog: Optional custom hardware catalog mapping.

    Returns:
        List of AllocatedSignal models sorted by (baseplate, slot).
    """
    if not signals:
        return []

    num_signals = len(signals)
    num_baseplates = max(1, (num_signals + charms_per_baseplate - 1) // charms_per_baseplate)

    model = cp_model.CpModel()

    # Decision variables for each signal
    baseplate_vars = []
    slot_vars = []
    pos_vars = []

    total_slots = num_baseplates * charms_per_baseplate

    for i in range(num_signals):
        bp = model.NewIntVar(1, num_baseplates, f"bp_{i}")
        slot = model.NewIntVar(1, charms_per_baseplate, f"slot_{i}")
        pos = model.NewIntVar(1, total_slots, f"pos_{i}")

        # Linear coordinate relation: pos == (bp - 1) * charms_per_baseplate + slot
        model.Add(pos == (bp - 1) * charms_per_baseplate + slot)

        baseplate_vars.append(bp)
        slot_vars.append(slot)
        pos_vars.append(pos)

    # Invariant 1: No two signals occupy the same slot
    model.AddAllDifferent(pos_vars)

    # Invariant 2: Ascending pair order contiguity for signals within the same cable
    for i in range(num_signals):
        sig_i = signals[i]
        if not sig_i.cable_id or sig_i.pair_no is None:
            continue
        for j in range(i + 1, num_signals):
            sig_j = signals[j]
            if not sig_j.cable_id or sig_j.pair_no is None:
                continue
            if sig_i.cable_id == sig_j.cable_id:
                if sig_i.pair_no < sig_j.pair_no:
                    model.Add(pos_vars[i] < pos_vars[j])
                elif sig_i.pair_no > sig_j.pair_no:
                    model.Add(pos_vars[j] < pos_vars[i])

    # Objective: Pack tightly from the beginning
    model.Minimize(sum(pos_vars))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("CP-SAT solver could not find a valid slot assignment.")

    allocations: List[AllocatedSignal] = []
    for i, sig in enumerate(signals):
        bp_val = solver.Value(baseplate_vars[i])
        slot_val = solver.Value(slot_vars[i])
        hw = resolve_hardware_assignment(
            sig.io_type,
            description=sig.description,
            tag=sig.tag,
            catalog=catalog,
        )

        allocations.append(
            AllocatedSignal(
                tag=sig.tag,
                io_type=sig.io_type,
                baseplate=bp_val,
                slot=slot_val,
                cioc=1,
                cabinet=1,
                cable_id=sig.cable_id,
                pair_no=sig.pair_no,
                description=sig.description,
                charm_model=hw.charm_model,
                charm_part_no=hw.charm_part_no,
                terminal_block_type=hw.terminal_block_type,
                terminal_block_part_no=hw.terminal_block_part_no,
                segregation=sig.segregation,
            )
        )

    # Sort deterministically by (baseplate, slot)
    allocations.sort(key=lambda a: (a.baseplate, a.slot))
    return allocations
