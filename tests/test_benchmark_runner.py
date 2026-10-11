import pytest
from src.benchmark.runner import (
    BenchmarkMetrics,
    run_single_benchmark,
    run_scalability_benchmark,
)
from src.benchmark.synthetic_generator import generate_synthetic_signals


def test_benchmark_metrics_dataclass():
    m = BenchmarkMetrics(
        signal_count=1000,
        cable_count=100,
        total_allocated_channels=1200,
        ciocs_used=15,
        cabinets_used=4,
        parse_time_seconds=0.05,
        macro_pack_seconds=0.02,
        micro_slot_seconds=0.15,
        audit_time_seconds=0.03,
        export_time_seconds=0.80,
        total_elapsed_seconds=1.05,
        peak_memory_mb=42.5,
        audit_passed=True,
        violation_count=0,
        violations=[],
        excel_size_bytes=150000,
    )
    d = m.to_dict()
    assert d["signal_count"] == 1000
    assert d["total_elapsed_seconds"] == 1.05
    assert d["peak_memory_mb"] == 42.5
    assert d["audit_passed"] is True

    md = m.to_summary_markdown()
    assert "1,000" in md or "1000" in md
    assert "Peak Memory" in md


def test_run_single_benchmark_small_batch():
    signals = generate_synthetic_signals(count=200, seed=42)
    metric = run_single_benchmark(
        signals=signals,
        export_excel=True,
    )

    assert metric.signal_count == 200
    assert metric.cable_count > 0
    assert metric.total_allocated_channels >= 200
    assert metric.ciocs_used > 0
    assert metric.cabinets_used > 0
    assert metric.macro_pack_seconds > 0
    assert metric.micro_slot_seconds > 0
    assert metric.audit_time_seconds > 0
    assert metric.export_time_seconds > 0
    assert metric.total_elapsed_seconds > 0
    assert metric.peak_memory_mb > 0
    assert metric.excel_size_bytes > 0
    assert metric.audit_passed is True
    assert metric.violation_count == 0
    assert len(metric.violations) == 0


def test_run_scalability_benchmark_suite():
    results = run_scalability_benchmark(
        signal_counts=[100, 300],
        export_excel=False,
        seed=101,
    )
    assert len(results) == 2
    assert results[0].signal_count == 100
    assert results[1].signal_count == 300
    assert all(r.audit_passed is True for r in results)
    assert all(r.violation_count == 0 for r in results)
    assert all(r.total_elapsed_seconds < 10.0 for r in results)
