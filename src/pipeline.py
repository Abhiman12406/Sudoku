"""End-to-end walking skeleton and hierarchical pipeline orchestrator."""

import io
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from src.domain.models import AllocatedSignal, SegregationPolicy, TechnicalQuery
from src.export.excel_export import export_allocation_to_excel
from src.ingestion.parser import parse_and_validate_signals
from src.solver.audit import verify_allocation_invariants
from src.solver.hierarchical_solver import solve_hierarchical_packing
from src.solver.walking_solver import solve_walking_skeleton


class PipelineResult:
    """Container holding allocations, deliverable Excel bytes, and generated TQs."""

    def __init__(
        self,
        allocations: List[AllocatedSignal],
        excel_bytes: bytes,
        tqs: List[TechnicalQuery],
    ):
        self.allocations = allocations
        self.excel_bytes = excel_bytes
        self.tqs = tqs

    def __iter__(self):
        # Enables backwards-compatible 2-element tuple unpacking:
        # allocations, out_bytes = run_walking_pipeline(...)
        return iter((self.allocations, self.excel_bytes))

    def __getitem__(self, index):
        return (self.allocations, self.excel_bytes, self.tqs)[index]

    def __len__(self):
        return 2

    def __repr__(self) -> str:
        return f"<PipelineResult: {len(self.allocations)} allocations, {len(self.tqs)} TQs, {len(self.excel_bytes)} bytes>"


def run_walking_pipeline(
    file_or_path_or_bytes: Union[str, Path, BinaryIO, bytes],
    charms_per_baseplate: int = 12,
    catalog: Optional[Dict[str, Any]] = None,
    return_tqs: bool = False,
    template_file_or_bytes: Optional[Union[str, Path, BinaryIO, bytes]] = None,
) -> Union[PipelineResult, Tuple[List[AllocatedSignal], bytes, List[TechnicalQuery]]]:
    """Execute end-to-end ingestion, fault-tolerant TQ isolation, CP-SAT allocation, and Excel export.

    Args:
        file_or_path_or_bytes: Path to input spreadsheet, binary buffer, or raw bytes.
        charms_per_baseplate: Number of CHARMs per baseplate (default: 12).
        catalog: Optional custom hardware catalog mapping.
        return_tqs: If True, returns explicit 3-tuple (allocations, excel_bytes, tqs).
        template_file_or_bytes: Optional blank customer Excel template to overlay onto.

    Returns:
        PipelineResult (unpackable as (allocations, excel_bytes) or providing .tqs).
    """
    if isinstance(file_or_path_or_bytes, bytes):
        buffer: Union[str, Path, BinaryIO] = io.BytesIO(file_or_path_or_bytes)
    else:
        buffer = file_or_path_or_bytes

    # 1. Parse and validate with fault isolation
    signals, tqs = parse_and_validate_signals(buffer)

    # 2. Solve CP-SAT slot assignment for valid signals
    if signals:
        allocations = solve_walking_skeleton(
            signals,
            charms_per_baseplate=charms_per_baseplate,
            catalog=catalog,
        )
    else:
        allocations = []

    # 3. Export populated Excel workbook with dedicated TQ_Log
    excel_bytes = export_allocation_to_excel(
        allocations,
        tqs=tqs,
        template_path_or_buffer=template_file_or_bytes,
        charms_per_bp=charms_per_baseplate,
    )

    if return_tqs:
        return allocations, excel_bytes, tqs

    return PipelineResult(allocations, excel_bytes, tqs)


def run_hierarchical_pipeline(
    file_or_path_or_bytes: Union[str, Path, BinaryIO, bytes],
    charms_per_baseplate: int = 12,
    baseplates_per_cioc: int = 8,
    spare_margin: float = 0.0,
    declared_sizes: Optional[dict[str, int]] = None,
    catalog: Optional[Dict[str, Any]] = None,
    return_tqs: bool = False,
    segregation_policy: Union[str, SegregationPolicy] = SegregationPolicy.CIOC,
    ciocs_per_cabinet: int = 4,
    template_file_or_bytes: Optional[Union[str, Path, BinaryIO, bytes]] = None,
) -> Union[PipelineResult, Tuple[List[AllocatedSignal], bytes, List[TechnicalQuery]]]:
    """Execute end-to-end two-stage hierarchical packing, independent audit, and Excel export.

    Args:
        file_or_path_or_bytes: Path to input spreadsheet, binary buffer, or raw bytes.
        charms_per_baseplate: Capacity of each physical baseplate (12).
        baseplates_per_cioc: Number of baseplates per CIOC card (8).
        spare_margin: Reserve capacity margin per CIOC (e.g. 0.0).
        declared_sizes: Optional dictionary of cable_id -> pair capacity.
        catalog: Optional custom hardware catalog mapping.
        return_tqs: If True, returns explicit 3-tuple (allocations, excel_bytes, tqs).
        segregation_policy: "CIOC" (CIOC-level segregation) or "CABINET" (Cabinet-level segregation).
        ciocs_per_cabinet: Number of CIOCs per Marshalling Cabinet (default: 4).
        template_file_or_bytes: Optional blank customer Excel template to overlay onto.

    Returns:
        PipelineResult (unpackable as (allocations, excel_bytes) or providing .tqs).
    """
    if isinstance(file_or_path_or_bytes, bytes):
        buffer: Union[str, Path, BinaryIO] = io.BytesIO(file_or_path_or_bytes)
    else:
        buffer = file_or_path_or_bytes

    # 1. Parse and validate with fault isolation
    signals, tqs = parse_and_validate_signals(buffer)

    # 2. Solve Two-Stage Hierarchical Packing
    if signals:
        allocations = solve_hierarchical_packing(
            signals,
            declared_sizes=declared_sizes,
            charms_per_baseplate=charms_per_baseplate,
            baseplates_per_cioc=baseplates_per_cioc,
            spare_margin=spare_margin,
            catalog=catalog,
            segregation_policy=segregation_policy,
            ciocs_per_cabinet=ciocs_per_cabinet,
        )

        # 3. Independent Post-Solve Hard Constraint Audit
        valid, errors = verify_allocation_invariants(
            allocations,
            charms_per_baseplate=charms_per_baseplate,
            baseplates_per_cioc=baseplates_per_cioc,
            segregation_policy=segregation_policy,
            ciocs_per_cabinet=ciocs_per_cabinet,
        )
        if not valid:
            raise RuntimeError(f"Allocation violated physical constraints: {'; '.join(errors)}")
    else:
        allocations = []

    # 4. Export populated Excel workbook with dedicated TQ_Log and all deliverable sheets
    excel_bytes = export_allocation_to_excel(
        allocations,
        tqs=tqs,
        template_path_or_buffer=template_file_or_bytes,
        charms_per_bp=charms_per_baseplate,
        bps_per_cioc=baseplates_per_cioc,
        ciocs_per_cabinet=ciocs_per_cabinet,
    )

    if return_tqs:
        return allocations, excel_bytes, tqs

    return PipelineResult(allocations, excel_bytes, tqs)
