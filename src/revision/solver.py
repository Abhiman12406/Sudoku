"""Stage-minimizing CP-SAT Revision Solver for DeltaV Electronic Marshalling."""

from collections import defaultdict
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
from ortools.sat.python import cp_model

from src.domain.hardware import resolve_hardware_assignment
from src.domain.models import AllocatedSignal, IOType, SegregationPolicy, Signal
from src.revision.classifier import (
    DiffStatus,
    RevisionDiffResult,
    SignalDiffItem,
    calculate_perturbation_delta,
    classify_revision_diff,
)


@dataclass
class RevisionAllocationResult:
    """Outcome of revision perturbation minimization solver."""
    allocations: List[AllocatedSignal] = field(default_factory=list)
    diff_result: RevisionDiffResult = field(default_factory=RevisionDiffResult)
    perturbation_score: int = 0
    moved_signals: List[AllocatedSignal] = field(default_factory=list)
    stationary_signals: List[AllocatedSignal] = field(default_factory=list)
    vacated_slots: List[Tuple[int, int, int]] = field(default_factory=list)  # (cioc, bp, slot)
    backfilled_slots: List[Tuple[int, int, int]] = field(default_factory=list)  # (cioc, bp, slot)


def solve_revision_allocation(
    rev_a_allocations: Sequence[AllocatedSignal],
    rev_b_signals: Sequence[Signal],
    diff_result: Optional[RevisionDiffResult] = None,
    charms_per_baseplate: int = 12,
    baseplates_per_cioc: int = 8,
    ciocs_per_cabinet: int = 4,
    segregation_policy: Union[str, SegregationPolicy] = SegregationPolicy.CIOC,
    catalog: Optional[Dict[str, Any]] = None,
    time_limit_seconds: float = 10.0,
) -> RevisionAllocationResult:
    """Allocate Revision B signals while freezing unchanged signals, backfilling vacated slots, and minimizing perturbation.

    Objective:
      min (10000 * Delta_cab + 1000 * Delta_cioc + 100 * Delta_bp + 10 * Delta_slot)

    Args:
        rev_a_allocations: Allocated signals from Revision A baseline.
        rev_b_signals: Newly requested signals for Revision B.
        diff_result: Optional precomputed RevisionDiffResult.
        charms_per_baseplate: Slots per baseplate (12).
        baseplates_per_cioc: Baseplates per CIOC (8).
        ciocs_per_cabinet: CIOCs per Marshalling Cabinet (4).
        segregation_policy: CIOC or CABINET level segregation.
        catalog: Optional custom hardware catalog mapping.
        time_limit_seconds: Max solver time in seconds.

    Returns:
        RevisionAllocationResult with frozen coordinates, backfilled slots, and perturbation metrics.
    """
    if diff_result is None:
        diff_result = classify_revision_diff(rev_a_allocations, rev_b_signals)

    policy = (
        SegregationPolicy.from_str(segregation_policy)
        if isinstance(segregation_policy, str)
        else segregation_policy
    )

    # 1. Map Rev A baseline allocations
    rev_a_by_tag: Dict[str, AllocatedSignal] = {}
    max_rev_a_cioc = 1

    for a in rev_a_allocations:
        if a.tag and not a.is_spare and a.tag.strip().upper() != "WIRED SPARE":
            rev_a_by_tag[a.tag] = a
        if a.cioc > max_rev_a_cioc:
            max_rev_a_cioc = a.cioc

    # 2. Identify vacated slots from DELETED signals
    vacated_slots: List[Tuple[int, int, int]] = []
    for del_item in diff_result.deleted:
        orig = rev_a_by_tag.get(del_item.tag)
        if orig:
            vacated_slots.append((orig.cioc, orig.baseplate, orig.slot))

    # 3. Freeze UNCHANGED signals (and non-physical MODIFIED signals) in their original Rev A coordinates
    final_allocations: List[AllocatedSignal] = []
    frozen_slots: Set[Tuple[int, int, int]] = set()
    stationary_signals: List[AllocatedSignal] = []

    # Map Rev B signals by tag for quick lookup
    rev_b_by_tag = {s.tag: s for s in rev_b_signals if s.tag}

    signals_to_freeze = list(diff_result.unchanged)
    physical_mods: List[SignalDiffItem] = []
    for mod_item in diff_result.modified:
        if not mod_item.is_physical_change:
            signals_to_freeze.append(mod_item)
        else:
            physical_mods.append(mod_item)

    for item in signals_to_freeze:
        orig = rev_a_by_tag[item.tag]
        b_sig = rev_b_by_tag[item.tag]
        coord = (orig.cioc, orig.baseplate, orig.slot)
        frozen_slots.add(coord)

        # Resolve hardware
        hw = resolve_hardware_assignment(b_sig, catalog=catalog)

        frozen_alloc = AllocatedSignal(
            tag=b_sig.tag,
            io_type=b_sig.io_type,
            cabinet=orig.cabinet,
            cioc=orig.cioc,
            baseplate=orig.baseplate,
            slot=orig.slot,
            cable_id=b_sig.cable_id or orig.cable_id,
            pair_no=b_sig.pair_no or orig.pair_no,
            description=b_sig.description or orig.description,
            charm_model=hw.charm_model,
            charm_part_no=hw.charm_part_no,
            terminal_block_type=hw.terminal_block_type,
            terminal_block_part_no=hw.terminal_block_part_no,
            segregation=b_sig.segregation or orig.segregation,
            is_spare=False,
        )
        final_allocations.append(frozen_alloc)
        stationary_signals.append(frozen_alloc)

    # 4. Signals that need slot allocation: physical MODIFIED and ADDED
    signals_to_assign: List[Tuple[Signal, Optional[AllocatedSignal], str]] = []  # (sig, orig_or_None, status)

    for mod_item in physical_mods:
        b_sig = rev_b_by_tag[mod_item.tag]
        orig = rev_a_by_tag.get(mod_item.tag)
        signals_to_assign.append((b_sig, orig, DiffStatus.MODIFIED.value))

    for add_item in diff_result.added:
        b_sig = rev_b_by_tag[add_item.tag]
        signals_to_assign.append((b_sig, None, DiffStatus.ADDED.value))

    backfilled_slots: List[Tuple[int, int, int]] = []
    moved_signals: List[AllocatedSignal] = []
    perturbation_score = 0

    if signals_to_assign:
        # Determine candidate physical slots
        slots_needed = len(signals_to_assign)
        total_ciocs = max_rev_a_cioc
        available_slots: List[Tuple[int, int, int, int]] = []  # (cabinet, cioc, bp, slot)

        def get_cab(c: int) -> int:
            return (c - 1) // ciocs_per_cabinet + 1

        max_rev_a_cab = get_cab(max_rev_a_cioc)
        total_ciocs = max(max_rev_a_cab * ciocs_per_cabinet, max_rev_a_cioc)
        if total_ciocs < 2:
            total_ciocs = 2

        if policy == SegregationPolicy.CABINET:
            has_train_a = any(s.segregation == "A" for s in rev_b_signals)
            has_train_b = any(s.segregation == "B" for s in rev_b_signals)
            if has_train_a and has_train_b and total_ciocs < 2 * ciocs_per_cabinet:
                total_ciocs = 2 * ciocs_per_cabinet

        # Check existing CIOCs
        for c in range(1, total_ciocs + 1):
            cab = get_cab(c)
            for b in range(1, baseplates_per_cioc + 1):
                for s in range(1, charms_per_baseplate + 1):
                    if (c, b, s) not in frozen_slots:
                        available_slots.append((cab, c, b, s))

        # If more slots needed, expand CIOCs
        while len(available_slots) < slots_needed:
            total_ciocs += 1
            cab = get_cab(total_ciocs)
            for b in range(1, baseplates_per_cioc + 1):
                for s in range(1, charms_per_baseplate + 1):
                    available_slots.append((cab, total_ciocs, b, s))

        # CP-SAT Model Formulation
        model = cp_model.CpModel()
        num_sigs = len(signals_to_assign)
        num_slots = len(available_slots)

        x: Dict[Tuple[int, int], cp_model.IntVar] = {}
        for i in range(num_sigs):
            for p in range(num_slots):
                x[i, p] = model.NewBoolVar(f"x_{i}_{p}")

        # Constraint: Each signal gets exactly one slot
        for i in range(num_sigs):
            model.Add(sum(x[i, p] for p in range(num_slots)) == 1)

        # Constraint: Each slot gets at most one signal
        for p in range(num_slots):
            model.Add(sum(x[i, p] for i in range(num_sigs)) <= 1)

        # Constraint: Segregation using Linearized Indicator Redundancy Cuts
        cioc_initial_trains: Dict[int, Set[str]] = defaultdict(set)
        cab_initial_trains: Dict[int, Set[str]] = defaultdict(set)
        for alloc in final_allocations:
            if alloc.segregation in ("A", "B"):
                cioc_initial_trains[alloc.cioc].add(alloc.segregation)
                cab_initial_trains[alloc.cabinet_id].add(alloc.segregation)

        all_candidate_ciocs = sorted(list({c for (_, c, _, _) in available_slots}))
        u_a: Dict[int, cp_model.IntVar] = {}
        u_b: Dict[int, cp_model.IntVar] = {}
        for c in all_candidate_ciocs:
            u_a[c] = model.NewBoolVar(f"cioc_{c}_train_a")
            u_b[c] = model.NewBoolVar(f"cioc_{c}_train_b")
            model.Add(u_a[c] + u_b[c] <= 1)

            if "A" in cioc_initial_trains.get(c, set()):
                model.Add(u_a[c] == 1)
                model.Add(u_b[c] == 0)
            elif "B" in cioc_initial_trains.get(c, set()):
                model.Add(u_b[c] == 1)
                model.Add(u_a[c] == 0)

        for i, (sig, orig, st) in enumerate(signals_to_assign):
            if sig.segregation == "A":
                for p, (cab, c, b, s) in enumerate(available_slots):
                    model.Add(x[i, p] <= u_a[c])
            elif sig.segregation == "B":
                for p, (cab, c, b, s) in enumerate(available_slots):
                    model.Add(x[i, p] <= u_b[c])

        if policy == SegregationPolicy.CABINET:
            all_candidate_cabs = sorted(list({cab for (cab, _, _, _) in available_slots}))
            u_cab_a: Dict[int, cp_model.IntVar] = {}
            u_cab_b: Dict[int, cp_model.IntVar] = {}
            for cab in all_candidate_cabs:
                u_cab_a[cab] = model.NewBoolVar(f"cab_{cab}_train_a")
                u_cab_b[cab] = model.NewBoolVar(f"cab_{cab}_train_b")
                model.Add(u_cab_a[cab] + u_cab_b[cab] <= 1)

                if "A" in cab_initial_trains.get(cab, set()):
                    model.Add(u_cab_a[cab] == 1)
                    model.Add(u_cab_b[cab] == 0)
                elif "B" in cab_initial_trains.get(cab, set()):
                    model.Add(u_cab_b[cab] == 1)
                    model.Add(u_cab_a[cab] == 0)

            for i, (sig, orig, st) in enumerate(signals_to_assign):
                if sig.segregation == "A":
                    for p, (cab, c, b, s) in enumerate(available_slots):
                        model.Add(x[i, p] <= u_cab_a[cab])
                elif sig.segregation == "B":
                    for p, (cab, c, b, s) in enumerate(available_slots):
                        model.Add(x[i, p] <= u_cab_b[cab])

        # Constraint: Cable Contiguity & In-Order Pair Alignment
        slots_per_cioc = baseplates_per_cioc * charms_per_baseplate
        pos_expr: Dict[int, Any] = {}
        for i in range(num_sigs):
            pos_expr[i] = sum(
                ((c - 1) * slots_per_cioc + (b - 1) * charms_per_baseplate + s) * x[i, p]
                for p, (cab, c, b, s) in enumerate(available_slots)
            )

        # Collect cable pairs across both frozen signals and signals to assign
        cable_all_pairs: Dict[str, List[Tuple[int, str, Any]]] = defaultdict(list)
        for alloc in final_allocations:
            if alloc.cable_id and alloc.pair_no is not None:
                cable_all_pairs[alloc.cable_id].append((alloc.pair_no, "frozen", alloc))

        for i, (sig, orig, st) in enumerate(signals_to_assign):
            if sig.cable_id and sig.pair_no is not None:
                cable_all_pairs[sig.cable_id].append((sig.pair_no, "assign", i))

        all_bps = sorted(list({(c, b) for (_, c, b, _) in available_slots}))

        for cbl_id, pair_items in cable_all_pairs.items():
            if not any(kind == "assign" for _, kind, _ in pair_items):
                continue

            sorted_items = sorted(pair_items, key=lambda it: it[0])
            max_pair = max(it[0] for it in sorted_items)
            for k in range(len(sorted_items) - 1):
                p1, kind1, val1 = sorted_items[k]
                p2, kind2, val2 = sorted_items[k + 1]
                if kind1 == "assign" and kind2 == "assign":
                    idx1, idx2 = val1, val2
                    model.Add(pos_expr[idx2] - pos_expr[idx1] == p2 - p1)

                    # Same CIOC
                    for c in all_candidate_ciocs:
                        c_slots = [p for p, (_, cioc_idx, _, _) in enumerate(available_slots) if cioc_idx == c]
                        model.Add(sum(x[idx1, p] for p in c_slots) == sum(x[idx2, p] for p in c_slots))

                    # Same baseplate if sub-12 or 12-pair
                    if max_pair <= 12:
                        for c_val, b_val in all_bps:
                            bp_slots = [p for p, (_, c, b, _) in enumerate(available_slots) if c == c_val and b == b_val]
                            model.Add(sum(x[idx1, p] for p in bp_slots) == sum(x[idx2, p] for p in bp_slots))

                elif kind1 == "frozen" and kind2 == "assign":
                    alloc1, idx2 = val1, val2
                    pos1 = (alloc1.cioc - 1) * slots_per_cioc + (alloc1.baseplate - 1) * charms_per_baseplate + alloc1.slot
                    model.Add(pos_expr[idx2] - pos1 == p2 - p1)

                    # Same CIOC as alloc1
                    c_slots = [p for p, (_, c, _, _) in enumerate(available_slots) if c == alloc1.cioc]
                    model.Add(sum(x[idx2, p] for p in c_slots) == 1)

                    # Same baseplate as alloc1 if sub-12 or 12-pair
                    if max_pair <= 12:
                        bp_slots = [p for p, (_, c, b, _) in enumerate(available_slots) if c == alloc1.cioc and b == alloc1.baseplate]
                        model.Add(sum(x[idx2, p] for p in bp_slots) == 1)

                elif kind1 == "assign" and kind2 == "frozen":
                    idx1, alloc2 = val1, val2
                    pos2 = (alloc2.cioc - 1) * slots_per_cioc + (alloc2.baseplate - 1) * charms_per_baseplate + alloc2.slot
                    model.Add(pos2 - pos_expr[idx1] == p2 - p1)

                    # Same CIOC as alloc2
                    c_slots = [p for p, (_, c, _, _) in enumerate(available_slots) if c == alloc2.cioc]
                    model.Add(sum(x[idx1, p] for p in c_slots) == 1)

                    # Same baseplate as alloc2 if sub-12 or 12-pair
                    if max_pair <= 12:
                        bp_slots = [p for p, (_, c, b, _) in enumerate(available_slots) if c == alloc2.cioc and b == alloc2.baseplate]
                        model.Add(sum(x[idx1, p] for p in bp_slots) == 1)

            if max_pair in (12, 24) and sorted_items[0][0] == 1 and sorted_items[0][1] == "assign":
                idx_first = sorted_items[0][2]
                slot_1_indices = [p for p, (_, _, _, s) in enumerate(available_slots) if s == 1]
                model.Add(sum(x[idx_first, p] for p in slot_1_indices) == 1)
        # Objective Function: Perturbation Minimization & Backfilling
        objective_terms = []

        for i, (sig, orig, st) in enumerate(signals_to_assign):
            for p, (cab, c, b, s) in enumerate(available_slots):
                cost = 0
                is_vacated = (c, b, s) in vacated_slots

                if orig is not None:
                    # Modified signal: penalize movement from original position hierarchically
                    orig_cab = orig.cabinet if orig.cabinet is not None else get_cab(orig.cioc)
                    d_cab = 1 if cab != orig_cab else 0
                    d_cioc = 1 if (d_cab or c != orig.cioc) else 0
                    d_bp = 1 if (d_cioc or b != orig.baseplate) else 0
                    d_slot = 1 if (d_bp or s != orig.slot) else 0

                    cost = (
                        10000 * d_cab
                        + 1000 * d_cioc
                        + 100 * d_bp
                        + 10 * d_slot
                    )
                else:
                    # Added signal: backfill vacated slots first, avoid new hardware
                    if is_vacated:
                        cost = 0
                    elif c <= max_rev_a_cioc:
                        cost = 5 + (b - 1) * 2 + s
                    else:
                        cost = 1000 * (c - max_rev_a_cioc) + 10000 * max(0, cab - get_cab(max_rev_a_cioc))

                objective_terms.append(cost * x[i, p])

        model.Minimize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(f"Revision solver failed to find feasible allocation: status={status}")

        # Extract solutions
        for i, (sig, orig, st) in enumerate(signals_to_assign):
            assigned_slot = None
            for p, (cab, c, b, s) in enumerate(available_slots):
                if solver.Value(x[i, p]) == 1:
                    assigned_slot = (cab, c, b, s)
                    break

            if assigned_slot is None:
                raise RuntimeError(f"Signal {sig.tag} had no assigned slot in solver solution")

            cab, c, b, s = assigned_slot
            hw = resolve_hardware_assignment(sig, catalog=catalog)

            alloc = AllocatedSignal(
                tag=sig.tag,
                io_type=sig.io_type,
                cabinet=cab,
                cioc=c,
                baseplate=b,
                slot=s,
                cable_id=sig.cable_id,
                pair_no=sig.pair_no,
                description=sig.description,
                charm_model=hw.charm_model,
                charm_part_no=hw.charm_part_no,
                terminal_block_type=hw.terminal_block_type,
                terminal_block_part_no=hw.terminal_block_part_no,
                segregation=sig.segregation,
                is_spare=False,
            )
            final_allocations.append(alloc)

            if (c, b, s) in vacated_slots:
                backfilled_slots.append((c, b, s))

            # Calculate perturbation for this signal using shared domain metric
            if orig is not None:
                signal_delta = calculate_perturbation_delta(orig, alloc, ciocs_per_cabinet=ciocs_per_cabinet)
                perturbation_score += signal_delta

                if signal_delta > 0:
                    moved_signals.append(alloc)
                else:
                    stationary_signals.append(alloc)
            else:
                # Added signal
                pass

    # Deterministic sort by (cioc, baseplate, slot)
    final_allocations.sort(key=lambda a: (a.cioc, a.baseplate, a.slot))

    return RevisionAllocationResult(
        allocations=final_allocations,
        diff_result=diff_result,
        perturbation_score=perturbation_score,
        moved_signals=moved_signals,
        stationary_signals=stationary_signals,
        vacated_slots=vacated_slots,
        backfilled_slots=backfilled_slots,
    )
