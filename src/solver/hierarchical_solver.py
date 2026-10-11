"""Two-Stage Hierarchical Packing Solver Orchestrator for DeltaV Electronic Marshalling."""

from typing import Any, Dict, List, Optional, Sequence, Union

from src.domain.cable import build_cable_blocks
from src.domain.models import AllocatedSignal, SegregationPolicy, Signal
from src.solver.macro_packer import solve_macro_packing
from src.solver.micro_slotter import slot_cable_blocks_in_cioc


def solve_hierarchical_packing(
    signals: Sequence[Signal],
    declared_sizes: Optional[Dict[str, int]] = None,
    charms_per_baseplate: int = 12,
    baseplates_per_cioc: int = 8,
    spare_margin: float = 0.0,
    time_limit_seconds: float = 10.0,
    catalog: Optional[Dict[str, Any]] = None,
    segregation_policy: Union[str, SegregationPolicy] = SegregationPolicy.CIOC,
    ciocs_per_cabinet: int = 4,
) -> List[AllocatedSignal]:
    """Execute two-stage hierarchical CP-SAT allocation.

    Stage 1: Macro CIOC packing assigns rigid CableBlocks to CIOC cards.
    Stage 2: Micro Baseplate slotting assigns cable pairs contiguously in ascending order.

    Args:
        signals: Input sequence of Signal objects.
        declared_sizes: Optional mapping of cable_id -> pair capacity.
        charms_per_baseplate: Physical baseplate capacity (default 12).
        baseplates_per_cioc: Number of baseplates per CIOC card (default 8).
        spare_margin: Optional percentage margin to keep empty on each CIOC (default 0.0).
        time_limit_seconds: Solver max execution time in seconds.
        catalog: Optional custom hardware catalog mapping.
        segregation_policy: "CIOC" (CIOC-level segregation) or "CABINET" (Cabinet-level segregation).
        ciocs_per_cabinet: Number of CIOCs per Marshalling Cabinet (default: 4).

    Returns:
        List of AllocatedSignal models sorted by (cioc, baseplate, slot).
    """
    if not signals:
        return []

    # 1. Construct CableBlock bundles
    cable_blocks = build_cable_blocks(signals, declared_sizes=declared_sizes)

    # 2. Stage 1: Macro-packing to CIOC containers
    slots_per_cioc = charms_per_baseplate * baseplates_per_cioc
    macro_result = solve_macro_packing(
        cable_blocks,
        slots_per_cioc=slots_per_cioc,
        spare_margin=spare_margin,
        time_limit_seconds=time_limit_seconds,
        segregation_policy=segregation_policy,
        ciocs_per_cabinet=ciocs_per_cabinet,
    )

    # 3. Stage 2: Micro-slotting within each CIOC
    all_allocations: List[AllocatedSignal] = []

    for cioc_id, blocks in macro_result.cioc_assignments.items():
        cioc_allocs = slot_cable_blocks_in_cioc(
            blocks,
            cioc_id=cioc_id,
            baseplates_per_cioc=baseplates_per_cioc,
            charms_per_baseplate=charms_per_baseplate,
            time_limit_seconds=time_limit_seconds,
            catalog=catalog,
            ciocs_per_cabinet=ciocs_per_cabinet,
        )
        all_allocations.extend(cioc_allocs)

    # Deterministic sort
    all_allocations.sort(key=lambda a: (a.cioc, a.baseplate, a.slot))
    return all_allocations
