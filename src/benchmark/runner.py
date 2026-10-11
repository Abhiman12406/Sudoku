"""Performance benchmark runner, memory profiler, and invariant verification telemetry."""

from dataclasses import asdict, dataclass, field
import io
import json
from pathlib import Path
import time
import tracemalloc
from typing import Any, Dict, List, Optional, Sequence, Union

from src.benchmark.synthetic_generator import generate_synthetic_signals
from src.domain.cable import build_cable_blocks
from src.domain.models import AllocatedSignal, SegregationPolicy, Signal
from src.export.excel_export import export_allocation_to_excel
from src.solver.audit import verify_allocation_invariants
from src.solver.macro_packer import solve_macro_packing
from src.solver.micro_slotter import slot_cable_blocks_in_cioc


@dataclass
class BenchmarkMetrics:
    """Comprehensive performance and rule-verification metrics for a benchmark run."""

    signal_count: int
    cable_count: int
    total_allocated_channels: int
    ciocs_used: int
    cabinets_used: int
    parse_time_seconds: float
    macro_pack_seconds: float
    micro_slot_seconds: float
    audit_time_seconds: float
    export_time_seconds: float
    total_elapsed_seconds: float
    peak_memory_mb: float
    audit_passed: bool
    violation_count: int
    violations: List[str] = field(default_factory=list)
    excel_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)

    def to_summary_markdown(self) -> str:
        """Render metrics as an executive markdown summary card."""
        status_badge = "PASSED (0 Violations)" if self.audit_passed else f"FAILED ({self.violation_count} Violations)"
        return (
            f"### Scalability Benchmark Results ({self.signal_count:,} Signals)\n\n"
            f"- **Status:** {status_badge}\n"
            f"- **Total Signals:** {self.signal_count:,} ({self.cable_count:,} multi-conductor cables)\n"
            f"- **Hardware Provisioned:** {self.ciocs_used} CIOCs across {self.cabinets_used} Cabinets\n"
            f"- **Total Channels (with Spares):** {self.total_allocated_channels:,}\n"
            f"- **Solve Timing Breakdown:**\n"
            f"  - Stage 1 (Macro Packing): `{self.macro_pack_seconds:.3f}s`\n"
            f"  - Stage 2 (Micro Slotting): `{self.micro_slot_seconds:.3f}s`\n"
            f"  - Invariant Verification Audit: `{self.audit_time_seconds:.3f}s`\n"
            f"  - Excel Deliverable Generation: `{self.export_time_seconds:.3f}s`\n"
            f"- **Total End-to-End Elapsed:** `{self.total_elapsed_seconds:.3f}s`\n"
            f"- **Peak Memory Consumption:** `{self.peak_memory_mb:.2f} MB`\n"
            f"- **Excel Workbook Size:** `{self.excel_size_bytes / 1024:.1f} KB`\n"
        )


def run_single_benchmark(
    signals: Optional[Sequence[Signal]] = None,
    signal_count: Optional[int] = None,
    seed: int = 42,
    charms_per_baseplate: int = 12,
    baseplates_per_cioc: int = 8,
    ciocs_per_cabinet: int = 4,
    spare_margin: float = 0.0,
    segregation_policy: Union[str, SegregationPolicy] = SegregationPolicy.CIOC,
    export_excel: bool = True,
    output_excel_path: Optional[Union[str, Path]] = None,
) -> BenchmarkMetrics:
    """Execute end-to-end benchmark on a single signal batch with high-resolution telemetry.

    Args:
        signals: Pre-existing signal batch (if None, synthetic batch of signal_count is generated).
        signal_count: Number of signals to generate if signals is None (default: 1000).
        seed: Random seed for reproducible generation.
        charms_per_baseplate: Number of slots per baseplate (12).
        baseplates_per_cioc: Number of baseplates per CIOC (8).
        ciocs_per_cabinet: Number of CIOCs per Marshalling Cabinet (4).
        spare_margin: Target reserve spare capacity.
        segregation_policy: CIOC or CABINET segregation.
        export_excel: Whether to generate the deliverable 5-tab Excel workbook.
        output_excel_path: Optional path to save the generated Excel deliverable.

    Returns:
        BenchmarkMetrics containing execution times, memory usage, and audit verification results.
    """
    tracemalloc.start()
    tracemalloc.reset_peak()

    t_start = time.perf_counter()

    # 1. Signals ingestion / generation
    t0 = time.perf_counter()
    if signals is None:
        count = signal_count or 1000
        test_signals = generate_synthetic_signals(count=count, seed=seed)
    else:
        test_signals = list(signals)

    # Build cable blocks
    blocks = build_cable_blocks(test_signals)
    t1 = time.perf_counter()
    parse_time = t1 - t0

    # 2. Stage 1: Macro-packing
    slots_per_cioc = charms_per_baseplate * baseplates_per_cioc
    t2 = time.perf_counter()
    macro_res = solve_macro_packing(
        blocks,
        slots_per_cioc=slots_per_cioc,
        spare_margin=spare_margin,
        segregation_policy=segregation_policy,
        ciocs_per_cabinet=ciocs_per_cabinet,
    )
    t3 = time.perf_counter()
    macro_pack_time = t3 - t2

    # 3. Stage 2: Micro-slotting
    all_allocations: List[AllocatedSignal] = []
    for c, blist in macro_res.cioc_assignments.items():
        cioc_allocs = slot_cable_blocks_in_cioc(
            blist,
            cioc_id=c,
            baseplates_per_cioc=baseplates_per_cioc,
            charms_per_baseplate=charms_per_baseplate,
            ciocs_per_cabinet=ciocs_per_cabinet,
        )
        all_allocations.extend(cioc_allocs)

    all_allocations.sort(key=lambda a: (a.cioc, a.baseplate, a.slot))
    t4 = time.perf_counter()
    micro_slot_time = t4 - t3

    # 4. Independent Verification Audit
    t5 = time.perf_counter()
    valid, errors = verify_allocation_invariants(
        all_allocations,
        charms_per_baseplate=charms_per_baseplate,
        baseplates_per_cioc=baseplates_per_cioc,
        segregation_policy=segregation_policy,
        ciocs_per_cabinet=ciocs_per_cabinet,
    )
    t6 = time.perf_counter()
    audit_time = t6 - t5

    # 5. Deliverable Export
    excel_size = 0
    t7 = time.perf_counter()
    if export_excel and all_allocations:
        excel_bytes = export_allocation_to_excel(
            all_allocations,
            charms_per_bp=charms_per_baseplate,
            bps_per_cioc=baseplates_per_cioc,
            ciocs_per_cabinet=ciocs_per_cabinet,
            segregation_policy=segregation_policy,
        )
        excel_size = len(excel_bytes)
        if output_excel_path:
            p = Path(output_excel_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(excel_bytes)
    t8 = time.perf_counter()
    export_time = t8 - t7

    t_end = time.perf_counter()
    total_elapsed = t_end - t_start

    # Memory measurement
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak_bytes / (1024 * 1024)

    active_ciocs = len(macro_res.cioc_assignments)
    active_cabs = max((a.cabinet for a in all_allocations), default=0)

    return BenchmarkMetrics(
        signal_count=len(test_signals),
        cable_count=len(blocks),
        total_allocated_channels=len(all_allocations),
        ciocs_used=active_ciocs,
        cabinets_used=active_cabs,
        parse_time_seconds=parse_time,
        macro_pack_seconds=macro_pack_time,
        micro_slot_seconds=micro_slot_time,
        audit_time_seconds=audit_time,
        export_time_seconds=export_time,
        total_elapsed_seconds=total_elapsed,
        peak_memory_mb=peak_mb,
        audit_passed=valid,
        violation_count=len(errors),
        violations=errors,
        excel_size_bytes=excel_size,
    )


def run_scalability_benchmark(
    signal_counts: Sequence[int] = (1000, 5000, 10000),
    export_excel: bool = True,
    seed: int = 42,
    output_dir: Optional[Union[str, Path]] = None,
) -> List[BenchmarkMetrics]:
    """Execute the full scalability benchmark suite across 1k, 5k, and 10k batches.

    Args:
        signal_counts: Batch sizes to profile (default: 1,000, 5,000, 10,000).
        export_excel: Whether to generate the deliverable workbook for each batch.
        seed: Random seed for reproducible generation.
        output_dir: Optional folder to save reports and deliverables.

    Returns:
        List of BenchmarkMetrics for each batch size.
    """
    results: List[BenchmarkMetrics] = []

    out_folder = Path(output_dir) if output_dir else None
    if out_folder:
        out_folder.mkdir(parents=True, exist_ok=True)

    for count in signal_counts:
        excel_path = out_folder / f"benchmark_deliverable_{count}_signals.xlsx" if out_folder else None
        metric = run_single_benchmark(
            signal_count=count,
            seed=seed,
            export_excel=export_excel,
            output_excel_path=excel_path,
        )
        results.append(metric)

    if out_folder:
        summary_path = out_folder / "benchmark_summary.json"
        summary_path.write_text(
            json.dumps([m.to_dict() for m in results], indent=2),
            encoding="utf-8",
        )

    return results
