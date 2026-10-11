"""Cabinet and hardware utilization metrics calculator for DeltaV allocations."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

from src.domain.models import AllocatedSignal


@dataclass
class CabinetSummaryRecord:
    cabinet_id: str
    ciocs_list: str
    cioc_count: int
    total_capacity: int
    active_loops: int
    wired_spares: int
    total_allocated: int
    free_spares: int
    utilization_pct: float

    @property
    def utilization_str(self) -> str:
        return f"{self.utilization_pct:.1f}%"


@dataclass
class OverallSummary:
    total_cabinets: int
    total_ciocs: int
    total_capacity: int
    total_active_loops: int
    total_wired_spares: int
    total_allocated: int
    total_free_spares: int
    overall_utilization_pct: float

    @property
    def utilization_str(self) -> str:
        return f"{self.overall_utilization_pct:.1f}%"


def compute_cabinet_summary(
    allocations: Sequence[AllocatedSignal],
    ciocs_per_cabinet: int = 4,
    bps_per_cioc: int = 8,
    charms_per_bp: int = 12,
) -> Tuple[List[CabinetSummaryRecord], OverallSummary]:
    """Compute cabinet-by-cabinet breakdown of channel counts, spares, and utilization.

    Args:
        allocations: Sequence of AllocatedSignal objects.
        ciocs_per_cabinet: Number of CIOCs per single-sided cabinet (default: 4).
        bps_per_cioc: Baseplates per CIOC carrier (default: 8).
        charms_per_bp: Slots per baseplate (default: 12).

    Returns:
        Tuple of (list_of_cabinet_records, overall_summary).
    """
    cioc_capacity = bps_per_cioc * charms_per_bp  # standard 96 channels

    # Group allocations by cabinet
    cab_active: Dict[int, int] = defaultdict(int)
    cab_spares: Dict[int, int] = defaultdict(int)
    cab_ciocs: Dict[int, Set[int]] = defaultdict(set)

    for alloc in allocations:
        cab_num = alloc.cabinet_id
        cab_ciocs[cab_num].add(alloc.cioc)
        if alloc.is_spare:
            cab_spares[cab_num] += 1
        else:
            cab_active[cab_num] += 1

    # Ensure at least Cabinet 1 is present if no allocations
    all_cab_nums = sorted(list(cab_ciocs.keys())) if cab_ciocs else [1]

    records: List[CabinetSummaryRecord] = []
    tot_cap = 0
    tot_active = 0
    tot_wired = 0
    tot_allocated = 0
    tot_free = 0
    all_ciocs_seen: Set[int] = set()

    for cab_num in all_cab_nums:
        ciocs = sorted(list(cab_ciocs.get(cab_num, set())))
        if not ciocs:
            ciocs = [1]
        all_ciocs_seen.update(ciocs)

        cioc_count = len(ciocs)
        # Cabinet capacity: fixed physical enclosure capacity (standard 384 channels)
        cab_cap = ciocs_per_cabinet * cioc_capacity
        active = cab_active.get(cab_num, 0)
        wired = cab_spares.get(cab_num, 0)
        allocated = active + wired
        free = max(0, cab_cap - allocated)
        util = round((allocated / cab_cap * 100.0), 2) if cab_cap > 0 else 0.0

        cioc_str = ", ".join(f"CIOC-{c:02d}" for c in ciocs)

        record = CabinetSummaryRecord(
            cabinet_id=f"CAB-{cab_num:02d}",
            ciocs_list=cioc_str,
            cioc_count=cioc_count,
            total_capacity=cab_cap,
            active_loops=active,
            wired_spares=wired,
            total_allocated=allocated,
            free_spares=free,
            utilization_pct=util,
        )
        records.append(record)

        tot_cap += cab_cap
        tot_active += active
        tot_wired += wired
        tot_allocated += allocated
        tot_free += free

    overall_util = round((tot_allocated / tot_cap * 100.0), 2) if tot_cap > 0 else 0.0
    overall = OverallSummary(
        total_cabinets=len(records),
        total_ciocs=len(all_ciocs_seen),
        total_capacity=tot_cap,
        total_active_loops=tot_active,
        total_wired_spares=tot_wired,
        total_allocated=tot_allocated,
        total_free_spares=tot_free,
        overall_utilization_pct=overall_util,
    )

    return records, overall
