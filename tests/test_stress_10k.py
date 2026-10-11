import time
from pathlib import Path
import pytest

from src.benchmark.runner import run_single_benchmark
from src.benchmark.synthetic_generator import generate_batch_10k


def test_end_to_end_10k_signals_under_60s(tmp_path):
    """Confirm end-to-end execution of 10,000 signals completes in under 60 seconds with 0 violations."""
    signals = generate_batch_10k(seed=42)
    assert len(signals) == 10000

    out_file = tmp_path / "deliverable_10k_test.xlsx"

    t0 = time.perf_counter()
    metric = run_single_benchmark(
        signals=signals,
        export_excel=True,
        output_excel_path=out_file,
    )
    t1 = time.perf_counter()
    total_time = t1 - t0

    # 1. Performance SLA: Under 60 seconds
    assert total_time < 60.0, f"Execution took {total_time:.2f}s, exceeding 60s SLA"
    assert metric.total_elapsed_seconds < 60.0

    # 2. Invariant Audit: Exactly 0 hard rule violations
    assert metric.audit_passed is True, f"Audit failed: {metric.violations}"
    assert metric.violation_count == 0
    assert len(metric.violations) == 0

    # 3. Scale guarantees: 10,000 signals across ~1,000 cables
    assert metric.signal_count == 10000
    assert 800 <= metric.cable_count <= 1200
    assert metric.ciocs_used > 0
    assert metric.cabinets_used > 0

    # 4. Memory Profiling: Monitored peak memory
    assert metric.peak_memory_mb > 0
    assert metric.peak_memory_mb < 2000.0  # Must be well under 2GB

    # 5. Deliverable Fidelity: Excel generated and non-empty
    assert out_file.exists()
    assert out_file.stat().st_size > 50000
