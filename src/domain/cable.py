"""Cable bundling and multi-conductor trunk cable block construction."""

from collections import defaultdict
from typing import Dict, List, Optional, Sequence

from src.domain.models import CableBlock, Signal

VALID_CABLE_SIZES = (2, 6, 12, 24)


def resolve_cable_size(max_pair_needed: int, declared_size: Optional[int] = None) -> int:
    """Determine the standard cable size (2, 6, 12, or 24 pairs)."""
    if declared_size is not None:
        if declared_size not in VALID_CABLE_SIZES:
            raise ValueError(
                f"Declared cable size {declared_size} is not a valid standard size ({VALID_CABLE_SIZES})"
            )
        if max_pair_needed > declared_size:
            raise ValueError(
                f"Required pairs ({max_pair_needed}) exceeds declared cable size ({declared_size})"
            )
        return declared_size

    for size in VALID_CABLE_SIZES:
        if size >= max_pair_needed:
            return size

    raise ValueError(
        f"Required pairs ({max_pair_needed}) exceeds maximum standard cable capacity (24 pairs)"
    )


def build_cable_blocks(
    signals: Sequence[Signal],
    declared_sizes: Optional[Dict[str, int]] = None,
) -> List[CableBlock]:
    """Group signals by cable ID into rigid CableBlock multi-conductor bundles.

    Args:
        signals: Input sequence of Signal objects.
        declared_sizes: Optional mapping of cable_id -> declared pair capacity.

    Returns:
        List of CableBlock domain objects sorted by cable ID.
    """
    declared = declared_sizes or {}
    cables_map: Dict[str, List[Signal]] = defaultdict(list)

    for sig in signals:
        cid = sig.cable_id if sig.cable_id else f"HR-{sig.tag}"
        cables_map[cid].append(sig)

    cable_blocks: List[CableBlock] = []

    for cable_id, sig_list in cables_map.items():
        # Validate pair numbers
        seen_pairs = set()
        max_pair = len(sig_list)

        for sig in sig_list:
            if sig.pair_no is not None:
                if sig.pair_no in seen_pairs:
                    raise ValueError(
                        f"Duplicate pair number {sig.pair_no} in cable '{cable_id}' for tag '{sig.tag}'"
                    )
                seen_pairs.add(sig.pair_no)
                if sig.pair_no > max_pair:
                    max_pair = sig.pair_no

        if max_pair > max(VALID_CABLE_SIZES):
            raise ValueError(
                f"Cable '{cable_id}' requires pair {max_pair}, which exceeds maximum capacity {max(VALID_CABLE_SIZES)}"
            )

        declared_sz = declared.get(cable_id)
        size = resolve_cable_size(max_pair, declared_size=declared_sz)

        # Sort signals by pair_no (or preserve order for unindexed)
        sorted_signals = sorted(
            sig_list,
            key=lambda s: s.pair_no if s.pair_no is not None else 9999,
        )

        # Extract segregation and io_group metadata
        seg = next((s.segregation for s in sig_list if s.segregation), None)
        grp = next((s.io_group for s in sig_list if s.io_group), None)

        cable_blocks.append(
            CableBlock(
                cable_id=cable_id,
                pair_count=size,
                signals=sorted_signals,
                io_group=grp,
                segregation=seg,
            )
        )

    # Sort blocks deterministically
    cable_blocks.sort(key=lambda b: b.cable_id)
    return cable_blocks
