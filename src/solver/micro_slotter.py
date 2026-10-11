"""Stage 2 Micro-Slotting Solver for contiguous, in-order baseplate channel assignment."""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple
from ortools.sat.python import cp_model

from src.domain.hardware import resolve_hardware_assignment, resolve_hardware_for_io
from src.domain.models import AllocatedSignal, CableBlock, IOType, Signal


def _get_candidate_placements(
    pair_count: int,
    baseplates_per_cioc: int = 8,
    charms_per_baseplate: int = 12,
) -> List[Tuple[int, int]]:
    """Generate valid (start_baseplate, start_slot) candidate coordinates.

    Invariants:
      - 24-pair cables span exactly 2 consecutive baseplates starting at slot 1.
      - 12-pair cables span exactly 1 baseplate starting at slot 1.
      - 6-pair cables occupy 6 contiguous slots on a single baseplate (slot 1 or 7).
      - 2-pair cables occupy 2 contiguous slots on a single baseplate (slot 1, 3, 5, 7, 9, 11).
      - Other sub-baseplate cables occupy contiguous slots on a single baseplate.
    """
    candidates: List[Tuple[int, int]] = []

    if pair_count == 24:
        for bp in range(1, baseplates_per_cioc):
            candidates.append((bp, 1))
    elif pair_count == 12:
        for bp in range(1, baseplates_per_cioc + 1):
            candidates.append((bp, 1))
    elif pair_count == 6:
        for bp in range(1, baseplates_per_cioc + 1):
            candidates.append((bp, 1))
            candidates.append((bp, 7))
    elif pair_count == 2:
        for bp in range(1, baseplates_per_cioc + 1):
            for s in (1, 3, 5, 7, 9, 11):
                candidates.append((bp, s))
    elif pair_count <= charms_per_baseplate:
        for bp in range(1, baseplates_per_cioc + 1):
            for s in range(1, charms_per_baseplate - pair_count + 2):
                candidates.append((bp, s))
    else:
        raise ValueError(f"Unsupported cable pair count {pair_count}")

    return candidates


def _get_occupied_slots(
    start_bp: int,
    start_slot: int,
    pair_count: int,
    charms_per_baseplate: int = 12,
) -> List[Tuple[int, int]]:
    """Return all (baseplate, slot) coordinates occupied by this placement."""
    slots: List[Tuple[int, int]] = []
    if pair_count == 24:
        # 12 on start_bp, 12 on start_bp + 1
        for s in range(1, charms_per_baseplate + 1):
            slots.append((start_bp, s))
        for s in range(1, charms_per_baseplate + 1):
            slots.append((start_bp + 1, s))
    else:
        for offset in range(pair_count):
            slots.append((start_bp, start_slot + offset))
    return slots


def slot_cable_blocks_in_cioc(
    cable_blocks: Sequence[CableBlock],
    cioc_id: int = 1,
    baseplates_per_cioc: int = 8,
    charms_per_baseplate: int = 12,
    time_limit_seconds: float = 10.0,
    catalog: Optional[Dict[str, Any]] = None,
    ciocs_per_cabinet: int = 4,
) -> List[AllocatedSignal]:
    """Micro-slotting solver for assigning CableBlocks inside a single CIOC card.

    Enforces:
      - 24-pair cables span exactly 2 consecutive baseplates in full.
      - 12-pair cables span exactly 1 baseplate in full.
      - 6-pair and 2-pair cables occupy contiguous slot sub-ranges.
      - Strict ascending pair order contiguity.
      - Explicit allocation of unused cable pairs as `WIRED SPARE` records.

    Args:
        cable_blocks: Sequence of CableBlocks assigned to this CIOC.
        cioc_id: CIOC card index (1..N).
        baseplates_per_cioc: Number of baseplates per CIOC (8).
        charms_per_baseplate: Capacity per baseplate (12).
        time_limit_seconds: Solver max execution time in seconds.

    Returns:
        List of AllocatedSignal models sorted by (baseplate, slot).
    """
    if not cable_blocks:
        return []

    # Sort blocks deterministically: larger blocks first, then by cable_id
    sorted_blocks = sorted(cable_blocks, key=lambda b: (-b.pair_count, b.cable_id))

    model = cp_model.CpModel()

    # Candidate placement decision variables
    z = {}
    candidate_map: Dict[int, List[Tuple[int, int]]] = {}

    for k, block in enumerate(sorted_blocks):
        candidates = _get_candidate_placements(
            block.pair_count,
            baseplates_per_cioc=baseplates_per_cioc,
            charms_per_baseplate=charms_per_baseplate,
        )
        candidate_map[k] = candidates
        for p_idx, (bp, slot) in enumerate(candidates):
            z[k, p_idx] = model.NewBoolVar(f"z_b{k}_p{p_idx}")

    # Constraint 1: Exactly one placement per block
    for k in range(len(sorted_blocks)):
        model.Add(sum(z[k, p_idx] for p_idx in range(len(candidate_map[k]))) == 1)

    # Constraint 2: No slot collision across blocks
    # Map each (bp, slot) to the (k, p_idx) placements that occupy it
    slot_to_placements = defaultdict(list)
    for k, block in enumerate(sorted_blocks):
        for p_idx, (bp, slot) in enumerate(candidate_map[k]):
            occ = _get_occupied_slots(bp, slot, block.pair_count, charms_per_baseplate=charms_per_baseplate)
            for coord in occ:
                slot_to_placements[coord].append((k, p_idx))

    for coord, plist in slot_to_placements.items():
        model.Add(sum(z[k, p_idx] for (k, p_idx) in plist) <= 1)

    # Objective: Pack tightly from earlier baseplates and slots
    objective_terms = []
    for k in range(len(sorted_blocks)):
        for p_idx, (bp, slot) in enumerate(candidate_map[k]):
            lin_pos = (bp - 1) * charms_per_baseplate + slot
            objective_terms.append(lin_pos * z[k, p_idx])

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(
            f"Stage 2 micro-slotting solver failed for CIOC {cioc_id} with status {solver.StatusName(status)}"
        )

    allocations: List[AllocatedSignal] = []

    for k, block in enumerate(sorted_blocks):
        chosen_bp, chosen_slot = None, None
        for p_idx, (bp, slot) in enumerate(candidate_map[k]):
            if solver.Value(z[k, p_idx]) == 1:
                chosen_bp, chosen_slot = bp, slot
                break

        if chosen_bp is None or chosen_slot is None:
            raise RuntimeError(f"No placement found for block {block.cable_id}")

        occ_coords = _get_occupied_slots(
            chosen_bp,
            chosen_slot,
            block.pair_count,
            charms_per_baseplate=charms_per_baseplate,
        )

        # Index existing signals by pair number
        signals_by_pair = dict(block.signals_by_pair)
        unindexed_signals = [s for s in block.signals if s.pair_no is None]

        # For unindexed signals, assign to available pair holes
        avail_pairs = [p for p in range(1, block.pair_count + 1) if p not in signals_by_pair]
        for unindexed, p in zip(unindexed_signals, avail_pairs):
            signals_by_pair[p] = unindexed

        # Allocate each pair 1..pair_count strictly in order
        for p in range(1, block.pair_count + 1):
            bp, slot = occ_coords[p - 1]
            if p in signals_by_pair:
                sig = signals_by_pair[p]
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
                        baseplate=bp,
                        slot=slot,
                        cioc=cioc_id,
                        cabinet=(cioc_id - 1) // ciocs_per_cabinet + 1,
                        cable_id=block.cable_id,
                        pair_no=p,
                        description=sig.description,
                        charm_model=hw.charm_model,
                        charm_part_no=hw.charm_part_no,
                        terminal_block_type=hw.terminal_block_type,
                        terminal_block_part_no=hw.terminal_block_part_no,
                        segregation=sig.segregation or block.segregation,
                        is_spare=False,
                    )
                )
            else:
                hw_spare = resolve_hardware_assignment(IOType.SPARE, catalog=catalog)
                allocations.append(
                    AllocatedSignal(
                        tag="WIRED SPARE",
                        io_type=IOType.SPARE,
                        baseplate=bp,
                        slot=slot,
                        cioc=cioc_id,
                        cabinet=(cioc_id - 1) // ciocs_per_cabinet + 1,
                        cable_id=block.cable_id,
                        pair_no=p,
                        description=f"Wired Spare Pair {p} ({block.cable_id})",
                        charm_model=hw_spare.charm_model,
                        charm_part_no=hw_spare.charm_part_no,
                        terminal_block_type=hw_spare.terminal_block_type,
                        terminal_block_part_no=hw_spare.terminal_block_part_no,
                        segregation=block.segregation,
                        is_spare=True,
                    )
                )

    allocations.sort(key=lambda a: (a.cioc, a.baseplate, a.slot))
    return allocations
