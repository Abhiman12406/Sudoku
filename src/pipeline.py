"""End-to-end walking skeleton pipeline orchestrator."""

import io
from pathlib import Path
from typing import BinaryIO, List, Tuple, Union

from src.domain.models import AllocatedSignal
from src.export.excel_export import export_allocation_to_excel
from src.ingestion.parser import parse_signal_file
from src.solver.walking_solver import solve_walking_skeleton


def run_walking_pipeline(
    file_or_path_or_bytes: Union[str, Path, BinaryIO, bytes],
    charms_per_baseplate: int = 12,
) -> Tuple[List[AllocatedSignal], bytes]:
    """Execute end-to-end ingestion, CP-SAT allocation, and Excel export.

    Args:
        file_or_path_or_bytes: Path to input spreadsheet, binary buffer, or raw bytes.
        charms_per_baseplate: Number of CHARMs per baseplate (default: 12).

    Returns:
        Tuple of (allocated signals list, generated output Excel bytes).
    """
    if isinstance(file_or_path_or_bytes, bytes):
        buffer: Union[str, Path, BinaryIO] = io.BytesIO(file_or_path_or_bytes)
    else:
        buffer = file_or_path_or_bytes

    # 1. Parse and validate
    signals = parse_signal_file(buffer)

    # 2. Solve CP-SAT slot assignment
    allocations = solve_walking_skeleton(signals, charms_per_baseplate=charms_per_baseplate)

    # 3. Export populated Excel workbook
    excel_bytes = export_allocation_to_excel(allocations)

    return allocations, excel_bytes
