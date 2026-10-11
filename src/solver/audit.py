"""Independent Post-Solve Hard Constraint Verification Audit Pass."""

from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from src.domain.models import AllocatedSignal


def verify_allocation_invariants(
    allocations: Sequence[AllocatedSignal],
    charms_per_baseplate: int = 12,
    baseplates_per_cioc: int = 8,
) -> Tuple[bool, List[str]]:
    """Verify 100% compliance with DeltaV physical and contiguity invariants.

    Checks:
      1. Physical slot uniqueness: No two allocations share (cioc, baseplate, slot).
      2. Baseplate capacity: 1 <= slot <= 12, 1 <= baseplate <= 8.
      3. Contiguity: Cable pairs occupy consecutive physical slots without gaps.
      4. Zero pair shuffling: Physical slot position strictly increases with pair_no.
      5. Strict boundary compliance:
         - 24-pair cables span exactly 2 consecutive baseplates (slots 1..12 each).
         - 12-pair cables span exactly 1 baseplate (slots 1..12).
         - Sub-baseplate cables (<= 12 pairs) never cross baseplate boundaries.

    Args:
        allocations: Sequence of AllocatedSignal objects.
        charms_per_baseplate: Number of slots per baseplate (12).
        baseplates_per_cioc: Number of baseplates per CIOC (8).

    Returns:
        Tuple of (is_valid, list_of_error_messages).
    """
    errors: List[str] = []

    if not allocations:
        return True, []

    # 1. Slot uniqueness & coordinate bounds
    occupied_coords: Dict[Tuple[int, int, int], str] = {}
    bp_usage: Dict[Tuple[int, int], int] = defaultdict(int)

    for alloc in allocations:
        coord = (alloc.cioc, alloc.baseplate, alloc.slot)
        if coord in occupied_coords:
            errors.append(
                f"Collision: Slot CIOC {alloc.cioc} BP {alloc.baseplate} Slot {alloc.slot} "
                f"occupied by both '{occupied_coords[coord]}' and '{alloc.tag}'"
            )
        occupied_coords[coord] = alloc.tag

        if alloc.slot < 1 or alloc.slot > charms_per_baseplate:
            errors.append(
                f"Slot out of bounds: Tag '{alloc.tag}' at slot {alloc.slot} (must be 1..{charms_per_baseplate})"
            )

        if alloc.baseplate < 1 or alloc.baseplate > baseplates_per_cioc:
            errors.append(
                f"Baseplate out of bounds: Tag '{alloc.tag}' at baseplate {alloc.baseplate} "
                f"(must be 1..{baseplates_per_cioc})"
            )

        bp_usage[(alloc.cioc, alloc.baseplate)] += 1

    for (c, bp), count in bp_usage.items():
        if count > charms_per_baseplate:
            errors.append(
                f"Baseplate capacity exceeded: CIOC {c} BP {bp} has {count} signals "
                f"(max {charms_per_baseplate})"
            )

    # 2. Cable contiguity and ascending pair order
    cables: Dict[str, List[AllocatedSignal]] = defaultdict(list)
    for alloc in allocations:
        if alloc.cable_id:
            cables[alloc.cable_id].append(alloc)

    slots_per_cioc = charms_per_baseplate * baseplates_per_cioc

    for cable_id, sig_list in cables.items():
        # Check pair_no presence
        with_pairs = [s for s in sig_list if s.pair_no is not None]
        if not with_pairs:
            continue

        # Sort by declared pair_no
        sorted_by_pair = sorted(with_pairs, key=lambda s: s.pair_no)  # type: ignore

        # Linear coordinate helper
        def get_pos(s: AllocatedSignal) -> int:
            return (s.cioc - 1) * slots_per_cioc + (s.baseplate - 1) * charms_per_baseplate + s.slot

        # Verify ascending pair order and strict contiguity
        for i in range(len(sorted_by_pair) - 1):
            curr = sorted_by_pair[i]
            nxt = sorted_by_pair[i + 1]
            pos_curr = get_pos(curr)
            pos_nxt = get_pos(nxt)

            # Pair shuffling check
            if pos_nxt <= pos_curr:
                errors.append(
                    f"Pair shuffling detected in cable '{cable_id}': Pair {curr.pair_no} at pos {pos_curr} "
                    f"is not before Pair {nxt.pair_no} at pos {pos_nxt}"
                )

            # Contiguity check: if pair numbers are consecutive, positions must be consecutive
            expected_delta = (nxt.pair_no or 0) - (curr.pair_no or 0)
            actual_delta = pos_nxt - pos_curr
            if expected_delta == 1 and actual_delta != 1:
                errors.append(
                    f"Non-contiguous cable allocation for '{cable_id}': Gap between Pair {curr.pair_no} "
                    f"(pos {pos_curr}) and Pair {nxt.pair_no} (pos {pos_nxt})"
                )

        # Boundary checks for standard sizes
        pair_count = max(s.pair_no for s in sorted_by_pair)  # type: ignore
        total_in_cable = len(sig_list)

        if total_in_cable == 24 or pair_count == 24:
            # 24-pair cable: must span exactly 2 consecutive baseplates starting at slot 1
            bps = sorted(list({s.baseplate for s in sig_list}))
            if len(bps) != 2 or bps[1] != bps[0] + 1:
                errors.append(
                    f"24-pair cable '{cable_id}' must span exactly 2 consecutive baseplates, got {bps}"
                )
            first = sorted_by_pair[0]
            if first.slot != 1:
                errors.append(
                    f"24-pair cable '{cable_id}' must start at slot 1, started at slot {first.slot}"
                )

        elif total_in_cable == 12 or pair_count == 12:
            # 12-pair cable: must span exactly 1 baseplate starting at slot 1
            bps = {s.baseplate for s in sig_list}
            if len(bps) != 1:
                errors.append(
                    f"12-pair cable '{cable_id}' must span exactly 1 baseplate, spans multiple {bps}"
                )
            first = sorted_by_pair[0]
            if first.slot != 1:
                errors.append(
                    f"12-pair cable '{cable_id}' must start at slot 1, started at slot {first.slot}"
                )

        elif total_in_cable <= 12:
            # Sub-baseplate cable: must not cross baseplate boundaries
            bps = {s.baseplate for s in sig_list}
            if len(bps) > 1:
                errors.append(
                    f"Sub-baseplate cable '{cable_id}' ({total_in_cable} pairs) crosses baseplate boundaries: {bps}"
                )

    return len(errors) == 0, errors
