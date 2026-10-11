#!/usr/bin/env python3
"""Evaluator-ready 1-click benchmark script and live performance telemetry demo."""

import argparse
import json
from pathlib import Path
import sys
import time

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.benchmark.runner import run_scalability_benchmark, run_single_benchmark
from src.domain.models import SegregationPolicy


def print_banner(signal_count: int, policy: str) -> None:
    print("=" * 80)
    print("   IO SIGNAL SUDOKU - INDUSTRIAL SCALABILITY & STRESS BENCHMARK")
    print(f"   Target Batch: {signal_count:,} Signals | Segregation Policy: {policy}")
    print("   System: Emerson DeltaV Electronic Marshalling Constraint Optimizer")
    print("=" * 80)
    print()


def print_metrics_card(metric) -> None:
    status_str = "\033[92mPASSED (0 Violations)\033[0m" if metric.audit_passed else f"\033[91mFAILED ({metric.violation_count} Violations)\033[0m"
    print("\n" + "-" * 80)
    print(f"BENCHMARK TELEMETRY RESULTS: {metric.signal_count:,} Signals")
    print("-" * 80)
    print(f"  • Invariant Audit Status:     {status_str}")
    print(f"  • Multi-conductor Trunk Cables: {metric.cable_count:,} bundles")
    print(f"  • Total Channels (inc Spares):{metric.total_allocated_channels:,} slots")
    print(f"  • Hardware Resources:         {metric.ciocs_used} CIOCs in {metric.cabinets_used} Marshalling Cabinets")
    print("  • High-Resolution Timings:")
    print(f"      - Ingestion & Cable Bundling:   {metric.parse_time_seconds * 1000:8.2f} ms")
    print(f"      - Stage 1: Macro CIOC Packing:  {metric.macro_pack_seconds * 1000:8.2f} ms")
    print(f"      - Stage 2: Micro Slotting:      {metric.micro_slot_seconds * 1000:8.2f} ms")
    print(f"      - Independent Invariant Audit:  {metric.audit_time_seconds * 1000:8.2f} ms")
    print(f"      - Excel Deliverable Generation: {metric.export_time_seconds * 1000:8.2f} ms")
    print(f"  • Total End-to-End Elapsed Time:    {metric.total_elapsed_seconds:8.3f} s  (Target: < 60.0 s)")
    print(f"  • Peak Memory Consumption:          {metric.peak_memory_mb:8.2f} MB")
    if metric.excel_size_bytes > 0:
        print(f"  • Excel Deliverable Workbook Size:  {metric.excel_size_bytes / 1024:8.1f} KB")
    print("-" * 80)

    if metric.violations:
        print("\n\033[91mHARD CONSTRAINT VIOLATIONS DETECTED:\033[0m")
        for v in metric.violations[:10]:
            print(f"  [X] {v}")
        if len(metric.violations) > 10:
            print(f"  ... and {len(metric.violations) - 10} more.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scalability Benchmark & Stress Hardening Demo for IO Signal Sudoku"
    )
    parser.add_argument(
        "--signals",
        type=int,
        default=10000,
        help="Number of synthetic instrumentation signals to generate (default: 10,000)",
    )
    parser.add_argument(
        "--suite",
        action="store_true",
        help="Run multi-batch scalability suite across 1k, 5k, and 10k batches",
    )
    parser.add_argument(
        "--counts",
        nargs="+",
        type=int,
        default=[1000, 5000, 10000],
        help="Batch sizes for suite run (default: 1000 5000 10000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible dataset generation (default: 42)",
    )
    parser.add_argument(
        "--policy",
        choices=["CIOC", "CABINET"],
        default="CIOC",
        help="Segregation verification policy (default: CIOC)",
    )
    parser.add_argument(
        "--spare-margin",
        type=float,
        default=0.0,
        help="Target reserve spare margin fraction (default: 0.0)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".benchmarks",
        help="Output directory to save summary reports and deliverables (default: .benchmarks)",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip Excel deliverable workbook generation to test pure solver speed",
    )

    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    export_excel = not args.no_export

    if args.suite:
        print_banner(sum(args.counts), args.policy)
        print(f"Running Scalability Suite across batches: {args.counts} ...\n")
        results = run_scalability_benchmark(
            signal_counts=args.counts,
            export_excel=export_excel,
            seed=args.seed,
            output_dir=out_dir,
        )
        print("\n" + "=" * 80)
        print("SCALABILITY BENCHMARK SUITE SUMMARY")
        print("=" * 80)
        print(f"{'Signals':<10} {'Cables':<10} {'CIOCs':<8} {'Time (s)':<12} {'Peak RAM (MB)':<15} {'Status':<15}")
        print("-" * 80)
        all_passed = True
        for m in results:
            status = "PASS (0 err)" if m.audit_passed else f"FAIL ({m.violation_count})"
            if not m.audit_passed:
                all_passed = False
            print(f"{m.signal_count:<10,d} {m.cable_count:<10,d} {m.ciocs_used:<8d} {m.total_elapsed_seconds:<12.3f} {m.peak_memory_mb:<15.2f} {status:<15}")
        print("=" * 80)
        print(f"\nSummary report saved to: {out_dir / 'benchmark_summary.json'}")
        return 0 if all_passed else 1

    # Single run
    print_banner(args.signals, args.policy)
    print(f"Generating and solving {args.signals:,} industrial signals...")
    t0 = time.perf_counter()
    excel_path = out_dir / f"deliverable_{args.signals}_signals.xlsx" if export_excel else None

    metric = run_single_benchmark(
        signal_count=args.signals,
        seed=args.seed,
        segregation_policy=SegregationPolicy.from_str(args.policy),
        spare_margin=args.spare_margin,
        export_excel=export_excel,
        output_excel_path=excel_path,
    )
    print_metrics_card(metric)

    if excel_path and excel_path.exists():
        print(f"\nExcel deliverable generated: {excel_path} ({excel_path.stat().st_size / 1024:.1f} KB)")

    return 0 if metric.audit_passed and metric.total_elapsed_seconds < 60.0 else 1


if __name__ == "__main__":
    sys.exit(main())
