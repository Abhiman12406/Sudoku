"""Tag-based diff classifier categorizing signals into UNCHANGED, MODIFIED, DELETED, and ADDED."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union

from src.domain.models import AllocatedSignal, Signal


class DiffStatus(str, Enum):
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    ADDED = "ADDED"


@dataclass
class SignalDiffItem:
    tag: str
    status: DiffStatus
    rev_a_signal: Optional[Union[Signal, AllocatedSignal]] = None
    rev_b_signal: Optional[Signal] = None
    changes: List[str] = field(default_factory=list)

    @property
    def is_physical_change(self) -> bool:
        """True if modification changes wiring, physical hardware, or cable groupings."""
        if self.status != DiffStatus.MODIFIED:
            return False
        # Any change to io_type, cable_id, pair_no, or segregation is physical
        return any(
            any(k in ch.lower() for k in ("io_type", "cable_id", "pair_no", "segregation"))
            for ch in self.changes
        )


@dataclass
class RevisionDiffResult:
    items: List[SignalDiffItem] = field(default_factory=list)

    @property
    def unchanged(self) -> List[SignalDiffItem]:
        return [item for item in self.items if item.status == DiffStatus.UNCHANGED]

    @property
    def modified(self) -> List[SignalDiffItem]:
        return [item for item in self.items if item.status == DiffStatus.MODIFIED]

    @property
    def deleted(self) -> List[SignalDiffItem]:
        return [item for item in self.items if item.status == DiffStatus.DELETED]

    @property
    def added(self) -> List[SignalDiffItem]:
        return [item for item in self.items if item.status == DiffStatus.ADDED]

    @property
    def total_rev_a(self) -> int:
        return len(self.unchanged) + len(self.modified) + len(self.deleted)

    @property
    def total_rev_b(self) -> int:
        return len(self.unchanged) + len(self.modified) + len(self.added)


def classify_revision_diff(
    rev_a: Sequence[Union[Signal, AllocatedSignal]],
    rev_b: Sequence[Signal],
) -> RevisionDiffResult:
    """Categorize signals between Rev A baseline and Rev B into UNCHANGED, MODIFIED, DELETED, and ADDED.

    Args:
        rev_a: Sequence of baseline signals or allocated signals from Revision A.
        rev_b: Sequence of newly received signals for Revision B.

    Returns:
        RevisionDiffResult grouping items with detailed field-level change logs.
    """
    map_a: Dict[str, Union[Signal, AllocatedSignal]] = {}
    for s in rev_a:
        if getattr(s, "is_spare", False) or s.tag.strip().upper() == "WIRED SPARE" or getattr(s, "io_type", None) == "SPARE":
            continue
        if s.tag:
            map_a[s.tag.strip()] = s

    map_b: Dict[str, Signal] = {}
    for s in rev_b:
        if getattr(s, "is_spare", False) or s.tag.strip().upper() == "WIRED SPARE" or getattr(s, "io_type", None) == "SPARE":
            continue
        if s.tag:
            map_b[s.tag.strip()] = s

    all_tags = sorted(list(set(map_a.keys()) | set(map_b.keys())))
    diff_items: List[SignalDiffItem] = []

    for tag in all_tags:
        sig_a = map_a.get(tag)
        sig_b = map_b.get(tag)

        if sig_a is not None and sig_b is None:
            diff_items.append(
                SignalDiffItem(
                    tag=tag,
                    status=DiffStatus.DELETED,
                    rev_a_signal=sig_a,
                    rev_b_signal=None,
                    changes=["Deleted loop in Rev B"],
                )
            )
        elif sig_a is None and sig_b is not None:
            diff_items.append(
                SignalDiffItem(
                    tag=tag,
                    status=DiffStatus.ADDED,
                    rev_a_signal=None,
                    rev_b_signal=sig_b,
                    changes=["New loop added in Rev B"],
                )
            )
        else:
            # Both present: detect modifications
            assert sig_a is not None and sig_b is not None
            changes: List[str] = []

            # Compare IO Type
            type_a = sig_a.io_type.value if hasattr(sig_a.io_type, "value") else str(sig_a.io_type)
            type_b = sig_b.io_type.value if hasattr(sig_b.io_type, "value") else str(sig_b.io_type)
            if type_a != type_b:
                changes.append(f"io_type: {type_a} -> {type_b}")

            # Compare Cable ID
            cbl_a = (sig_a.cable_id or "").strip()
            cbl_b = (sig_b.cable_id or "").strip()
            if cbl_a != cbl_b:
                changes.append(f"cable_id: {cbl_a or '-'} -> {cbl_b or '-'}")

            # Compare Pair No
            p_a = sig_a.pair_no
            p_b = sig_b.pair_no
            if p_a != p_b:
                changes.append(f"pair_no: {p_a or '-'} -> {p_b or '-'}")

            # Compare Segregation
            seg_a = (sig_a.segregation or "").strip().upper()
            seg_b = (sig_b.segregation or "").strip().upper()
            if seg_a != seg_b:
                changes.append(f"segregation: {seg_a or 'None'} -> {seg_b or 'None'}")

            # Compare Description
            desc_a = (sig_a.description or "").strip()
            desc_b = (sig_b.description or "").strip()
            if desc_a != desc_b:
                changes.append(f"description: '{desc_a}' -> '{desc_b}'")

            if changes:
                diff_items.append(
                    SignalDiffItem(
                        tag=tag,
                        status=DiffStatus.MODIFIED,
                        rev_a_signal=sig_a,
                        rev_b_signal=sig_b,
                        changes=changes,
                    )
                )
            else:
                diff_items.append(
                    SignalDiffItem(
                        tag=tag,
                        status=DiffStatus.UNCHANGED,
                        rev_a_signal=sig_a,
                        rev_b_signal=sig_b,
                        changes=[],
                    )
                )

    return RevisionDiffResult(items=diff_items)
